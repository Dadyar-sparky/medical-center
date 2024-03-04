import asyncio
from telegram.ext import PollAnswerHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext
import os
import mysql.connector
import re
from mysql.connector import Error
from telegram.ext import ConversationHandler, MessageHandler
from telegram.ext import filters
from datetime import datetime, timedelta
import schedule
from threading import Thread
import time
import logging
from tqdm.contrib import telegram

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


# Database setup
def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host='localhost',       # Or the appropriate host where your DB is running
            user='root',   # Replace with your MySQL username
            password= os.getenv('PASSWORD'), # Replace with your MySQL password
            database='doctors_appointment' # Replace with your database name
        )
        if connection.is_connected():
            db_info = connection.get_server_info()
            print("Connected to MySQL Server version", db_info)
            return connection
    except Error as e:
        print("Error while connecting to MySQL", e)
        return None


#monitoring...................................................



logging.basicConfig(level=logging.INFO, filename='bot.log', filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



def handle_user_message(update, context):
    user_id = update.effective_user.id  # Get user ID
    message_text = update.message.text  # Get message text
    try:
        # Process the user message here
        logger.info(f"User {user_id} sent message: {message_text}")
        # Respond to the user
    except Exception as e:
        logger.error(f"Failed to process message from user {user_id} due to error: {e}")









NAME, AGE, GENDER, PHONE, CONFIRM = range(5)

#validation.................................
def is_valid_name(name):
    # Matches names with English letters, Kurdish letters, and spaces
    return re.match(r"^[A-Za-z\u0600-\u06FF\s]+$", name) is not None
def is_valid_age(age):
    try:
        age = int(age)
        return 0 <= age <= 120
    except ValueError:
        return False
def is_valid_gender(gender):
    return gender.lower() in ['male', 'female', 'نێر','مێ']
def is_valid_phone(phone):
    phone_no_spaces = phone.replace(" ", "")
    return re.match(r"^(\d{11})$", phone_no_spaces) is not None


#Start     Registration      .................................

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data['is_registering'] = True
    # Proceed with asking for the name or the first step in registration
    await update.message.reply_text('تکایە <b> ناوی سیانی بنوسە:</b>', parse_mode='HTML')
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if not is_valid_name(name):
        await update.message.reply_text('ببورە شێوازی نوسینی ناوەکەت هەڵەیە ')
        return NAME
    context.user_data['name'] = update.message.text
    await update.message.reply_text('تکایە <b>تەمەن:</b>', parse_mode='HTML')
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age = update.message.text
    if not is_valid_age(age):
        await update.message.reply_text('ببورە شێوازی نوسینی تەمەنەکەت هەڵەیە ')
        return AGE
    context.user_data['age'] = update.message.text
    await update.message.reply_text('تکایە <b>ڕەگەز:</b>', parse_mode='HTML')
    return GENDER

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text
    if not is_valid_gender(gender):
        await update.message.reply_text('ببورە  نوسینی ڕەگەز دەبێت (" نێر " یان " مێ " ) ')
        return GENDER
    context.user_data['gender'] = update.message.text
    await update.message.reply_text('تکایە <b>ژمارە مۆبایل:</b>', parse_mode='HTML')

    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    if not is_valid_phone(phone):
        await update.message.reply_text('تکایە  نوسینی ژمارە مۆبایل دەبێت  ١١ ڕەقەم بێت ')
        return PHONE
    user_id = update.message.from_user.id
    user_data = context.user_data
    name = user_data['name']
    age = user_data['age']
    gender = user_data['gender']
    phone_number = update.message.text
    doctor_id = user_data.get('doctor_id', 1)  # Default to 1 if not set

    if connection := connect_to_db():
        try:
            cursor = connection.cursor()
            # Check the last registration time for the user
            cursor.execute("SELECT registration_time FROM registrations WHERE user_id = %s ORDER BY registration_time DESC LIMIT 1", (user_id,))
            if last_registration := cursor.fetchone():
                last_registration_time = last_registration[0]
                current_time = datetime.now()
                time_diff = current_time - last_registration_time

                if time_diff.total_seconds() < 43200:  # 12 hours in seconds
                    await update.message.reply_text( ' /Start 👈🏻 تۆ پێشتر تۆمارت کردووە. تکایە دوای 12 کاتژمێر هەوڵبدەوە.')
                    return ConversationHandler.END

            # If no registration in the last 12 hours, proceed with registration
            insert_query = "INSERT INTO registrations (user_id, name, age, gender, phone_number, doctor_id) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (user_id, name, age, gender, phone_number, doctor_id))
            connection.commit()  # Commit the transaction
            await update.message.reply_text('/Start 👈🏻 دەست خۆش، زانیاریەکانت تۆمار کران.')
        except Error as e:
            print("Error while inserting into MySQL", e)
            await update.message.reply_text('/Start 👈🏻  ببورە، کێشەیەک هەیە لە ناو تۆمارکردندا.')
        finally:
            cursor.close()
            connection.close()
    else:
        await update.message.reply_text('/Start 👈🏻  ببورە، کێشەیەک هەیە لە پەیوەندیکردن بە داتابەیس.')

    return ConversationHandler.END

def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('bale', start_registration)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
    },
    fallbacks=[CommandHandler('naxer', cancel)],
)
bale_handler = CommandHandler('bale', start_registration)





#feedback---------------poll-------------feedback------------------poll----------------


async def show_feedback_poll_options(update: Update, context: CallbackContext.DEFAULT_TYPE):
    query = update.callback_query
    # Define your feedback and poll options here
    keyboard = [
        [InlineKeyboardButton(" ڕاپرسی📊", callback_data='start_poll')],
        [InlineKeyboardButton(" پێشنیار✍️", callback_data='prompt_feedback')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='back_to_main')]
        # You can add more options here
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # If it's a callback query, edit the message, otherwise send a new message

    await query.edit_message_text(text="لێرە دوو بەشمان هەیە  بۆ وەرگرتنی بیروڕا و پێشنیاری سەردانی کەرانمان🩷🩷", reply_markup=reply_markup)









#poll................................................................................
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update

    answer = update.poll_answer
    user_id = answer.user.id
    selected_options = answer.option_ids  # This is a list of selected option indices

    if connection := connect_to_db():
        try:
            cursor = connection.cursor()
            # Check if the user has voted in the last 24 hours
            cursor.execute("SELECT MAX(vote_time) FROM poll_results WHERE user_id = %s", (user_id,))
            if last_vote_time := cursor.fetchone()[0]:
                # Calculate the time difference between now and the last vote time
                time_diff = datetime.now() - last_vote_time
                if time_diff.total_seconds() < 43200:  # 24 hours in seconds
                    # Notify the user that they need to wait longer

                    # Inside handle_poll_answer, when sending the warning message
                    warning_message =  await context.bot.send_message(chat_id=user_id, text="🚫ببورە تۆ ڕۆژانە تەنها  یەک جار دەتوانیت بەژدەربیت")
                    # Store the message ID
                    context.user_data['last_warning_message_id'] = warning_message.message_id
                    await asyncio.sleep(5)

                    # Delete the warning message
                    await context.bot.delete_message(chat_id=user_id, message_id=warning_message.message_id)

                    # Optionally clear the stored message ID
                    del context.user_data['last_warning_message_id']


                    return

            insert_query = "INSERT INTO poll_results (user_id, vote, vote_time) VALUES (%s, %s, NOW())"
            # If the user hasn't voted in the last 24 hours or at all, proceed to record their vote
            for option_id in selected_options:
                vote = context.bot_data['poll_options'][option_id]  # Retrieve option text based on index
                cursor.execute(insert_query, (user_id, vote))
            connection.commit()
            warning_message = await context.bot.send_message(chat_id=user_id,
                                                             text="🩵 سوپاس بۆ بەژداری کردنت ")
            # Store the message ID
            context.user_data['last_warning_message_id'] = warning_message.message_id
            await asyncio.sleep(5)

            # Delete the warning message
            await context.bot.delete_message(chat_id=user_id, message_id=warning_message.message_id)

            # Optionally clear the stored message ID
            del context.user_data['last_warning_message_id']
        except Error as e:
            print(f"Error inserting into MySQL: {e}")
        finally:
            cursor.close()
            connection.close()


async def start_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id
    # Define your poll question and options here
    question = "ڕات چیە لەسەر خزمەت گوزاریەکانی  کۆمەڵگاکەمان .  . .  .  .  . .  ؟🤔"
    options = ["زۆر باشن", "باشن", "مامناوەندن", "خراپن"]
    message = await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question=question,
        options=options,
        is_anonymous=False,  # Adjust based on your needs
        allows_multiple_answers=False  # Important
    )
    # Store the poll message ID for potential future use
    context.user_data['poll_message_id'] = message.message_id
    # Store options in bot_data for later retrieval
    context.bot_data['poll_options'] = options

    # Prepare the back button
    keyboard = [[InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='feedback_poll_back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    submenu_text = "دەتوانی دەنگدانەکەت پێشکەش بکەیت یان بگەڕێیەوە."
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)






#feedback.......................................................................

async def prompt_feedback(update: Update, context: CallbackContext.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id
    context.user_data['awaiting_feedback'] = True  # Set the flag to indicate we're waiting for feedback
    await query.edit_message_text(text=" پێشنیارت چیە بۆمان. . . . . . . . . . ""\n\n\n""")
    keyboard = [[InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='feedback_poll_back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    submenu_text = "  ڕەخنە و پێشنیارت یاخوود هەرکێشەیەکت هەیە لەکاتی بەکار هێنانی ئەم بارنامە 🧏🏻‍♂️ ""\n\n\n"" لە خوارەوە بۆمان بنوسە📝"
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)
async def receive_feedback(update: Update, context: CallbackContext.DEFAULT_TYPE):
    # Check if we're expecting feedback
    if context.user_data.get('awaiting_feedback'):
        feedback = update.message.text
        user_id = update.message.from_user.id

        # Connect to the database
        db = connect_to_db()
        cursor = db.cursor()

        # SQL query to insert feedback
        query = "INSERT INTO user_feedback (user_id, feedback) VALUES (%s, %s)"
        values = (user_id, feedback)

        try:
            cursor.execute(query, values)
            db.commit()  # Commit to save changes

            warning_message = await context.bot.send_message(chat_id=user_id,
                                                             text="   سوپاس بۆ پێشنیارەکەت  پێشنیارەکەت وەرگیرا 🧡 ")
            # Store the message ID
            context.user_data['last_warning_message_id'] = warning_message.message_id
            await asyncio.sleep(7)

            # Delete the warning message
            await context.bot.delete_message(chat_id=user_id, message_id=warning_message.message_id)

            # Optionally clear the stored message ID
            del context.user_data['last_warning_message_id']
        except Exception as e:
            print(e)  # Log the error
            warning_message = await context.bot.send_message(chat_id=user_id,
                                                             text="ببورە کێشەیەک هەیە بە زووترین کات چارەسەر دەکرێت.")
            # Store the message ID
            context.user_data['last_warning_message_id'] = warning_message.message_id
            await asyncio.sleep(7)

            # Delete the warning message
            await context.bot.delete_message(chat_id=user_id, message_id=warning_message.message_id)

            # Optionally clear the stored message ID
            del context.user_data['last_warning_message_id']
        finally:
            cursor.close()
            db.close()

        del context.user_data['awaiting_feedback']  # Clear the flag after processing
    else:
        await update.message.reply_text("/Start 👈🏻  ببورە هیچ تێگەشتنێکم  نیە و نازانم مەبەستت چیە    ")



#Starrrrrrrrrrrrrrrrrrrrrrrrrrtttttttttttttttttttt...............................................

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = ("✅ بەخێربێن  بۆ    "
                "( كۆمەڵگەی پزیشكی بەخشین - ھەڵەبجەی شەھید 🏨 )"
                "\n"
                "\n"
                "🔵 لێرەدا دەتوانن  زانیارتان دەست بەکەوێت   سەبارەت بە سەرجەم خزمەتگوزاریەکان  کۆمەڵگاکەمان   وە چەندین زانیاری تر  ....."
                "\n"
                "\n"
                "داواکاریەکەت هەڵبژێرە :- ")

    keyboard = [
        [InlineKeyboardButton("📆 خشتەی_دەوامی_کۆمەڵگەکەمان", callback_data='time'),
         InlineKeyboardButton("👨🏻‍⚕️🧑🏼‍⚕️ دکتۆرەکانمان ", callback_data='doctors')],
        [InlineKeyboardButton("📝 ناونوسین ", callback_data='register'),
         InlineKeyboardButton("📣 زانیاری تەندرووستی", callback_data=' Health')],
        [InlineKeyboardButton("ڕاپرسی و پێشنیار 📊", callback_data='poll_feedback')],
        [InlineKeyboardButton(" سەردانی پەیج بکە 🌐", url='https://www.facebook.com/Baxshin.halabjaaa?mibextid=ZbWKwL')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if context.user_data.get('is_registering', False):
        # Reset registration flag
        context.user_data['is_registering'] = False
        # Optionally send a message indicating the reset
        message= await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="خۆتۆمار کردنەکەت هەڵوەشایەوە")
        await asyncio.sleep(3)

        # Delete the message
        await context.bot.delete_message(chat_id=update.effective_chat.id,
                                         message_id=message.message_id)


    # Check if the update is from a callback query (button press)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=greeting, reply_markup=reply_markup)
    else:
        # For the first time the menu is sent, use the message context
        await update.message.reply_text(text=greeting, reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
     query = update.callback_query
     await query.answer()

     if query.data == 'back_to_main':
         # Close the poll if it's still active
         poll_message_id = context.user_data.get('poll_message_id')
         if poll_message_id:
             try:
                 await context.bot.stop_poll(chat_id=query.message.chat_id, message_id=poll_message_id)
             except Exception as e:
                 print(f"Error closing the poll: {e}")

             # Attempt to delete the poll message
             try:
                 await context.bot.delete_message(chat_id=query.message.chat_id, message_id=poll_message_id)
                 # Remove the stored poll message ID after deletion
                 del context.user_data['poll_message_id']
             except Exception as e:
                 print(f"Error deleting poll message: {e}")

         # Attempt to delete the warning message if its ID is stored
         warning_message_id = context.user_data.get('last_warning_message_id')
         if warning_message_id:
             try:
                 await context.bot.delete_message(chat_id=query.message.chat_id, message_id=warning_message_id)
                 # Remove the stored warning message ID after deletion
                 del context.user_data['last_warning_message_id']
             except Exception as e:
                 print(f"Error deleting warning message: {e}")

         # Proceed to show the main menu
         await start(update, context)

     elif query.data == 'register':
        await register(update, context)
     elif query.data.startswith('r'):
         # Extract doctor_id from callback data
         doctor_id = int(query.data[1:])  # Convert 'r1' to 1, 'r2' to 2, etc.
         context.user_data['doctor_id'] = doctor_id  # Store doctor_id in user_data

         # Prompt user to start registration process
         await query.edit_message_text(' <b>دڵنیایت دەتەوێت ناوی خۆت تۆمار بکەی   👈🏻  /bale </b>', parse_mode='HTML')

        # await query.edit_message_text('دڵنیایت دەتەوێت ناوی خۆت تۆمار بکەی   👈🏻  /bale    ' )
         return  # Exit the function to avoid processing other conditions

     elif query.data == 'subscribe':
         await subscribe_user(query.from_user.id, query, context)
     elif query.data == 'unsubscribe':
         await unsubscribe_user(query.from_user.id, query, context)
     elif query.data == ' Health':
        await  Start_Health(update, context)

     elif query.data == 'poll_feedback':
        await show_feedback_poll_options(update, context)
     elif query.data == 'start_poll':
        await start_poll(update, context)
     elif query.data == 'prompt_feedback':
        await prompt_feedback(update, context)
     elif query.data == 'feedback_poll_back':
             # User clicked on "Back" button from the feedback prompt
             # Check if we have a poll message to delete
             if 'poll_message_id' in context.user_data:
                 try:
                     await context.bot.delete_message(chat_id=query.message.chat_id,
                                                      message_id=context.user_data['poll_message_id'])
                     del context.user_data['poll_message_id']  # Remove the stored message ID
                 except Exception as e:
                     print(f"Failed to delete the poll message: {e}")
             await show_feedback_poll_options(update, context)

     elif query.data == 'back_to_submenu':
         await show_time_submenu(update, context)
     elif query.data == 'time':
        await show_time_submenu(update, context)
     elif query.data == 'doctors':
        await show_doctors_submenu(update, context)
     elif query.data == 'show_doctor_da_submenu':
        await show_doctor_da_submenu(update, context)
     elif query.data == 'show_doctor_db_submenu':
        await show_doctor_db_submenu(update, context)
     elif query.data == 'show_doctor_dc_submenu':
        await show_doctor_dc_submenu(update, context)
     elif query.data == 'show_doctor_dd_submenu':
        await show_doctor_dd_submenu(update, context)
     elif query.data == 'show_doctor_de_submenu':
        await show_doctor_de_submenu(update, context)
     elif query.data == 'show_doctor_df_submenu':
        await show_doctor_df_submenu(update, context)
     elif query.data == 'show_doctor_dg_submenu':
        await show_doctor_dg_submenu(update, context)
     elif query.data == 'show_doctor_dh_submenu':
        await show_doctor_dh_submenu(update, context)
     elif query.data == 'show_doctor_di_submenu':
        await show_doctor_di_submenu(update, context)
     elif query.data == 'show_doctor_dj_submenu':
        await show_doctor_dj_submenu(update, context)
     elif query.data == 'show_doctor_dk_submenu':
        await show_doctor_dk_submenu(update, context)
     elif query.data == 'show_doctor_dl_submenu':
        await show_doctor_dl_submenu(update, context)
     elif query.data == 'show_doctor_dm_submenu':
        await show_doctor_dm_submenu(update, context)

     elif query.data == 'da':
        await show_doctor_da_submenu(update, context)
     elif query.data == 'db':
        await show_doctor_db_submenu(update, context)
     elif query.data == 'dc':
        await show_doctor_dc_submenu(update, context)
     elif query.data == 'dd':
        await show_doctor_dd_submenu(update, context)
     elif query.data == 'de':
        await show_doctor_de_submenu(update, context)
     elif query.data == 'df':
        await show_doctor_df_submenu(update, context)
     elif query.data == 'dg':
        await show_doctor_dg_submenu(update, context)
     elif query.data == 'dh':
        await show_doctor_dh_submenu(update, context)
     elif query.data == 'di':
        await show_doctor_di_submenu(update, context)
     elif query.data == 'dj':
        await show_doctor_dj_submenu(update, context)
     elif query.data == 'dk':
        await show_doctor_dk_submenu(update, context)
     elif query.data == 'dl':
         await show_doctor_dl_submenu(update, context)
     elif query.data == 'dm':
         await show_doctor_dm_submenu(update, context)
    # Implement similar elif blocks for 'db' to 'dk'
     elif query.data in ['0', '1', '2', '3', '4', '5', '6']:
        await show_day_image_and_paragraph(update, context, query.data)
    # Sub-options handling
     elif query.data == 'da_1':

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428346808_820210890119471_6718604767696019233_n.jpg"
         caption = ("👨🏻‍⚕️دکتۆر عماد جلال حبیب اللە\n\n\n"
                    "✅دکتۆرا (بۆردی عێڕاقی)لە نەخۆشییەکانی قوڕگ و گوێ و لوت\n\n"
                    "✅پزیشکی پسپۆڕی نەشتەرگەری غودە و لیکە ڕژێنەکان،نەشتەرگەری جیوبەکان بە نازۆر ، نەشتەرگەری ڕێککاری لوت و گوێ\n\n"
                    "🌞 ڕۆژانی یەک شەممە\n"
                    "🌙شەوانی پێنج شەممە\n\n"
                    "لە کۆمەڵگەکەمان کلینیکی دەبێت\n")
         keyboard = InlineKeyboardMarkup([
             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_da_submenu')]
         ])

         # Attempt to delete the original message
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption
         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id, caption=caption,
                                      reply_markup=keyboard)
     elif query.data == 'db_1':

        image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428157763_819875916819635_1201469557214334019_n.jpg"

        caption = ("👨🏻‍⚕️دکتۆر ھاوژین شەماڵ ڕەمەزان\n\n\n"

                   "✅پزیشکی پسپۆڕی خۆراک و گەشە🩺\n\n"

                   "✅بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی\n\n"

                   "🗓️ڕۆژانی پێنج شەممە\n\n"

                   "لە کۆمەڵگەکەمان کلینیکی دەبێت")

        keyboard = InlineKeyboardMarkup([

            [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_db_submenu')]

        ])

        # Delete the original message

        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

        # Send a new photo message with caption

        await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id, caption=caption,

                                     reply_markup=keyboard)
     elif query.data == 'dc_1':

        image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\426253073_813587160781844_8729817826525790033_n.jpg"

        caption = ("👩🏻‍⚕️دکتۆرە گوڵان عبداللە محمد\n\n\n"
    "✅ دکتۆرا (بۆردی عەرەبی )لە نەخۆشییەکانی منداڵان و تازە لە دایک بووان🩺\n\n"
    "✅بەکالۆیۆس لە هەناوی و نەشتەرگەری گشتی\n\n"
    "🗓️ڕۆژانی چوار شەممە\n\n"
    "لە کۆمەڵگەکەمان کلینیکی دەبێت")

        keyboard = InlineKeyboardMarkup([

            [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dc_submenu')]

        ])

        # Delete the original message

        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

        # Send a new photo message with caption

        await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id, caption=caption,

                                     reply_markup=keyboard)
     elif query.data == 'dc_2':
        # Implement your logic to show appointment details for doctor 'da'

        image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428378256_819555166851710_6132044194718734946_n.jpg"

        caption= ( "👨🏻‍⚕️دکتۆر ئومێد حسن عزیز\n\n\n"
    "✅هەڵگری بڕوانامەی دکتۆرا لە نەخۆشیەکانی منداڵان🩺\n\n"
    "✅بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی\n\n"
    "🗓️ڕۆژانی پێنج شەممە\n\n"
    "لە کۆمەڵگەکەمان کلینیکی دەبێت🏨")


        keyboard = InlineKeyboardMarkup([

                          [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dc_submenu')]])
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

                 # Send a new photo message with caption

        await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                              caption=caption,

                                              reply_markup=keyboard)
     elif query.data == 'dd_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\427959971_818176590322901_207991053954362177_n.jpg"

         caption = ("👨🏻‍⚕️دکتۆر ڕەوەند حمەعلی هەڵەبجەیی\n\n\n"
    "✅پزیشکی پسپۆڕی ئێسک و شکاوی\n\n"
    "✅بۆردی عێڕاقی لە نەشتەرگەری ئێسک و شکاوی،گۆڕینی جومگە و فەقەرات\n\n"
    "✅بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی\n\n"
    "🗓️ڕۆژانی شەممە و سێ شەممە\n\n"
    "لە کۆمەڵگەکەمان کلینیکی دەبێت")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dd_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,

                                      reply_markup=keyboard)
     elif query.data == 'dd_2':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\427915320_816916003782293_571368880491072784_n.jpg"

         caption = ( "👨🏻‍⚕️دکتۆر هەردی لطیف محی الدین\n\n\n"
"✅پسپۆڕی ئێسک و شکاوی 🩺\n\n"
"✅دکتۆرا (بۆردی عرەبی )لە نەشتەرگەری ئێسک و شکاوی\n\n"
"✅بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی\n\n"
"🗓️ڕۆژانی یەک شەممە و دوو شەممە\n\n"
"لە کۆمەڵگەکەمان کلینیکی دەبێت.")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dd_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,

                                      reply_markup=keyboard)
     elif query.data == 'de_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\426250212_813801610760399_7299527177653771838_n.jpg"

         caption = ("👩🏻‍⚕️دکتۆرە پەیمان احمد کوێخا\n\n\n"
"☑️پسپۆڕی نەخۆشییەکانی پێست و لەیزەرو جوانکاری💉\n\n"
"☑️بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی\n\n"
"🗓️ڕۆژانی شەممە، یەک شەممە، سێ شەممە، چوار شەممە\n\n"
"لە کۆمەڵگەکەمان کلینیکی دەبێت\n\n"
"✅لەیزەری موو\n"
"✅لەیزەری کاربۆنی\n"
"✅لەیزەری CO2\n"
"✅پلازما\n"
"✅میزۆی پەڵەو ژێرچاو و سپیکردنەوەی پێست\n"
"✅ئامێری RF\n"
"✅هایدرافیشال\n"
"✅لابردنی خاڵ\n")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_de_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,

                                      reply_markup=keyboard)
     elif query.data == 'df_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\425887667_812864080854152_1716046577258252482_n.jpg"

         caption = ("👨🏻‍⚕️دکتۆر شوان ابوبکر احمد\n\n\n"
                    "✅پزیشکی پسپۆڕی مێشک و دەمار و ماسولکە 🧠\n\n"  
                    "✅بەکالۆریۆس لە هەناووی و نەشتەرگەری گشتی\n\n"
                    "🗓️ڕۆژانی دووشەممە\n\n"
                    "لە کۆمەڵگەکەمان کلینیکی دەبێت\n\n"                
                    "🟣 باشترین ئامێری هێڵکاری دەمارو ماسولکە لە کۆمەڵگەکەمان بەردەستە و لە خزمەت چارەخوازاندایە")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_df_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,

                                      reply_markup=keyboard)
     elif query.data == 'dg_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428628933_821471999993360_1866608834076263759_n.jpg"

         caption = ("👨🏻‍⚕️ دکتۆر ماکوان محمد عبدالکریم\n\n\n"
                    "✅پزیشکی پسپۆڕی نەخۆشییە دەرونییەکان\n\n"
                    "✅ دکتۆرا (بۆردی عربی)-(Psych) CABMS\n\n"
                    "✅ دکتۆرا (بۆردی عێراقی)-(Psych) FIBMS\n\n"
                    "✅ بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی (M.B.Ch.\n\n"
                    "🗓️ڕۆژانی یەک شەممە\n\n"
                    "لە کۆمەڵگەکەمان کلینیکی دەبێت")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dg_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                         reply_markup=keyboard)
     elif query.data == 'dg_2':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428638193_821472033326690_4346873123953324809_n.jpg"

         caption = ("👨🏻‍💼 به‌ڕێز محمد وەلی عبدالله\n\n\n"
                    "✅چارەسەرکاری دەروونی\n\n"
                    "✅ بەکالۆریۆس له دەروونزانی\n\n"
                    "✅ بۆ ڕاوێژکاری دەروونی، کۆمەڵایەتی، پەروەردەی\n\n"
                    "🗓️ڕۆژانی (یەک شەممە) لە کۆمەڵگەکەمان کلینیکی دەبێت")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dg_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                         reply_markup=keyboard)
     elif query.data == 'dh_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\425419401_811622980978262_1016859104670458108_n.jpg"

         caption =( "👩🏻‍⚕️دکتۆرە سارە شاکر محمود\n\n\n"
"✅پسپۆڕی نەشتەرگەری و نەخۆشییەکانی ژنان و منداڵ بوون\n\n"
"✅پسپۆڕی نەزۆکی و چاودێری خانمانی دووگیان\n\n"
"✅هەڵگری بڕوانامەی دکتۆرا (بۆرد عرەبی) لە نەخۆشییەکانی ژنان و منداڵبوون و چارەسەری نەزۆکی\n\n"
"✅بە کالۆریۆس لە هەناوی و نەشتەرگەری گشتی(الجامعة المستنصرية-بغداد)\n"
"M.B.CH.B-C.A.B.O.G\n\n"
"🗓️ڕۆژانی شەممە,2 شەممە,4شەممە،5شەممە\n\n"
"لە کۆمەڵگەکەمان کلینیکی دەبێت 🏨")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dh_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                         reply_markup=keyboard)
     elif query.data == 'di_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\423315753_809784414495452_4682723229711074663_n.jpg"

         caption = ( "👨🏻‍⚕️دکتۆر کمال عزیز عبدالقادر\n\n\n"
"✅پسپۆڕی نەشتەرگەری گشتی🩺\n\n"
"✅هەڵگری بڕوانامەی دکتۆرا (بۆرد)لە نەشتەرگەری گشتی\n\n"
"✅بەکالۆیۆس لە هەناوی و نەشتەرگەری گشتی\n\n"
"🗓️هەموو ڕۆژانی هەفتە جگە یەک شەممە\n"
"لە کۆمەڵگەکەمان کلینیکی دەبێت")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_di_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                      reply_markup=keyboard)
     elif query.data == 'dj_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\423134153_808657607941466_6155903525631042898_n.jpg"

         caption = ("👨🏻‍⚕️دکتۆر صباح نصرالدين\n\n\n"
                    "  ✅پسپۆری ددان "
                    "\n\n"
             "🟣دروستکردنی هۆڵیوودسمایل بۆ چارەخوازێکی خۆشەویست بە جوانترین شێوە و هەرزانترین نرخ لە کۆمەڵگەکەمان\n"
)

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dj_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                      reply_markup=keyboard)
     elif query.data == 'dk_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\421327953_804739151666645_1898178043354051397_n.jpg"

         caption = (
    "👨🏻‍⚕️دکتۆر ڕێباز ابراهیم احمد\n\n\n"
    "✅پسپۆری نەشتەرگەری گورچیلە و میزەڕۆ / پڕۆستات ونەزۆکی پیاوان\n\n"
    "✅دكتۆرا (بۆرد) له‌ نەشتەرگەری گورچیلە و میزەڕۆ\n"
    "M.B.Ch.B -FKHCMS(Urology)\n\n"
    "🗓️ڕۆژانی (سێ شەممە - پێنج شەممە )\n\n"
    "لە کۆمەڵگەکەمان کلینیکی دەبێت 🏨")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dk_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                      reply_markup=keyboard)
     elif query.data == 'dl_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428391520_822363546570872_7071939532358657334_n.jpg"

         caption = (
             "🧑🏻‍⚕️دکتۆرە ئایار عمر عەلی\n\n\n"
             "✅پسپۆڕی جومگەو  ڕۆماتیزم و فەقەرات\n\n"
             "✅بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی\n\n"
        
             "🗓️ڕۆژانی شەممە، 2شەممە ،4 شەممە\n\n"
             "لە کۆمەڵگەکەمان کلینیکی دەبێت 🏨")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dl_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                      reply_markup=keyboard)
     elif query.data == 'dm_1':
         # Implement your logic to show appointment details for doctor 'da'

         image_url_or_file_id = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\429923496_826558442818049_2816869789159114584_n.jpg"

         caption = (
             "👨🏻‍⚕️دکتۆر حسین عەلی ڕەمەزان\n\n\n"
             "✅پسپۆڕی نەشتەرگەری و نەخۆشیییەکانی چاو\n\n"
             "✅بەکالۆریۆس لە هەناوی و نەشتەرگەری گشتی\n\n"

             "🗓️ڕۆژ و شەوی سێ شەممە \n\n"
             "لە کۆمەڵگەکەمان کلینیکی دەبێت 🏨")

         keyboard = InlineKeyboardMarkup([

             [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='show_doctor_dm_submenu')]])
         await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

         # Send a new photo message with caption

         await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url_or_file_id,
                                      caption=caption,
                                      reply_markup=keyboard)
     else:
          await query.edit_message_text(text=f"Selected option: {query.data} 🚀")


async def show_doctor_da_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id


    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️دکتۆر عماد جلال حبیب اللە", callback_data='da_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text , reply_markup=reply_markup)
async def show_doctor_db_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️دکتۆر ھاوژین شەماڵ ڕەمەزان ", callback_data='db_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_dc_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query or update
        chat_id = query.message.chat_id
        message_id_to_delete = query.message.message_id

        submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
        keyboard = [
            [InlineKeyboardButton("👩🏻‍⚕️دکتۆرە گوڵان عبداللە محمد", callback_data='dc_1')],
            [InlineKeyboardButton("👨🏻‍⚕️دکتۆر  ئومێد حسن عزیز", callback_data='dc_2')],
            [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_dd_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️دکتۆر ڕەوەند حمەعلی هەڵەبجەیی ", callback_data='dd_1')],
        [InlineKeyboardButton("👨🏻‍⚕️دکتۆر هەردی لطیف محی الدین", callback_data='dd_2')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

# Remember to define similar functions for other doctors ('db' to 'dk') as needed.
async def show_doctor_de_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👩🏻‍⚕️دکتۆرە پەیمان احمد کوێخا", callback_data='de_1')],

        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_df_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️دکتۆر شوان ابوبکر احمد ", callback_data='df_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_dg_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️ دکتۆر ماکوان محمد عبدالکریم", callback_data='dg_1')],
        [InlineKeyboardButton("👨🏻‍💼 به‌ڕێز محمد وەلی عبدالله", callback_data='dg_2')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_dh_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👩🏻‍⚕️دکتۆرە سارە شاکر  محمود", callback_data='dh_1')],

        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_di_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️دکتۆر کمال عزیز عبدالقادر  ", callback_data='di_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_dj_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️د. صباح نصرالدين", callback_data='dj_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)


async def show_doctor_dk_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️د. ڕێباز ابراهیم احمد", callback_data='dk_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)

async def show_doctor_dl_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("🧑🏻‍⚕️ د.ئایار عمر عەلی", callback_data='dl_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)
async def show_doctor_dm_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = ("🔵دکتۆرەکان .     .     .     .     .     .     .     .     .     .     .     .     .     .     .     👨🏻‍⚕️🧑🏼‍⚕️\n\n\n"
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n")
    keyboard = [
        [InlineKeyboardButton("👨🏻‍⚕️ د.حسین عەلی ڕەمەزان ", callback_data='dm_1')],
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='doctors')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)








async def show_time_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query or update
    chat_id = query.message.chat_id
    message_id_to_delete = query.message.message_id

    submenu_text = (" 📌  بۆ زانینی خشتەی_دەوامی_کۆمەڵگەکەمان  لەم هەفتەدا   .    .    .    .    .    .    .    "  "\n\n" 
                    "🟢پسوڵەی بینینی پزیشک تەنها (3000 )دینار\n\n"
                         "🔵پسوڵەی سۆنار تەنها (7000)دینار\n\n\n"
                        
                   
                    "لە کاتژمێر 🕒 2:00ی پاشنیوەڕۆ🌞 تا 🕚 11:00 شەو🌙\n\n"
                    "بە ڕووی هاوڵاتیاندا کراوەیە\n\n"
                    "\n"  " ڕۆژێک هەڵبژێرە  .   .  .  .  "
                    )
    keyboard = [
        [InlineKeyboardButton(" 🔸 ١ شەمە ", callback_data='1'),
         InlineKeyboardButton("🔸 شەمە", callback_data='0')],
        [InlineKeyboardButton("🔸 ٣ شەمە", callback_data='3'),
         InlineKeyboardButton("🔸 ٢ شەمە", callback_data='2')],
        [InlineKeyboardButton("🔸 ٥ شەمە", callback_data='5'),
         InlineKeyboardButton("🔸 ٤ شەمە", callback_data='4')],
        [InlineKeyboardButton("🔸 هەینی", callback_data='6')],
        [InlineKeyboardButton("گەڕانەوە⬅️", callback_data='back_to_main')]

    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
    await context.bot.send_message(chat_id=chat_id, text=submenu_text, reply_markup=reply_markup)




async def show_day_image_and_paragraph(update: Update, context: ContextTypes.DEFAULT_TYPE, day: str):
    query = update.callback_query or update
    day_info = {
        '0': {
            "paragraph": "..............................................................................................................................."
                         "#خشتەی_دەوامی_کۆمەڵگەکەمان بۆ ڕۆژی #شەممە\n"
                         "10/2/2024\n"
                         "______________\n"
                         "✅دەوامی ڕۆژ\n"
                         "👩🏻‍⚕️دکتۆرە سارە شاکر محمود /پسپۆڕی ژنان و منداڵبوون\n"
                         "07508036300 ☎️\n"
                         "👨🏻‍⚕️دکتۆر ڕەوەند حمەعلی هەڵەبجەیی /پسپۆڕی ئێسک و شکاوی\n"
                         "07511817571 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە ئایار عمر عەلی /پسپۆڕی جومگە و ڕۆماتیزم\n"
                         "07511817571 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە پەیمان احمد کوێخا /پسپۆڕی پێست و لەیزەر\n"
                         "07511872424 ☎️\n"
                         "👨🏻‍⚕️دکتۆر کمال عزیز عبدالقادر /پسپۆڕی نەشتەرگەری گشتی\n"
                         "07511817571 ☎️\n"
                         "👨🏻‍⚕️دکتۆر ابراهیم اسکندر عبداللە /پسپۆڕی قوڕگ و گوێ و لوت\n"
                         "07511872525 ☎️\n"
                         "🔻🔻🔻🔻🔻🔻🔻🔻🔻\n"
                         "✅دەوامی شەو\n"
                         "👩🏻‍⚕️دکتۆرە دێکان محمود / پزیشکی گشتی\n"
                         "07511817571 ☎️\n"
                         "👨🏻‍⚕️دکتۆر عیرفان احمد / پسپۆڕی سۆنار\n"
                         "07511817571 ☎️\n"
                         "_______\n",
            "image": "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\427805439_821079836699243_4785772399696945066_n.jpg"
        },
        '1': {
            "paragraph": "..............................................................................................................................."
                         "#خشتەی_دەوامی_کۆمەڵگەکەمان بۆ ڕۆژی #یەک_شەممە\n"
                         "11/2/2024\n"
                         "___\n"
                         "✅دەوامی ڕۆژ\n"
                         "👨🏻‍⚕️دكتۆر هەردی لطيف محی الدین / پسپۆڕی ئێسک و شکاوی\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دكتۆر ماکوان محمد عبدالکریم /پسپۆڕی نەخۆشییە دەروونییەکان\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دكتۆر بەرهەم زین الدین صاحب / پسپۆڕی هەناوی\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دكتۆر حسین عەلی ڕەمەزان  / پسپۆڕی نەخۆشییەکانی چاو\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دكتۆر نەشئەدین عزیز محمد /پسپۆڕی نەشتەرگەری مێشک و فەقەرات و دەمارەکان\n"
                         "07511817571☎️\n"
                         "👩🏻‍⚕️دکتۆرە پەیمان احمد کوێخا/ پسپۆی پێست و لەیزەر\n"
                         "07511872424☎️\n"
                         "👨🏻‍⚕️دکتۆر عماد جلال حبیب اللە / پسپۆڕی قورگ وگوێ و لوت غودە ولیکەڕژێنەکان\n"
                         "07511872525☎️\n"
                         "👨🏻‍⚕️ بەڕێز محمد وەلی عبداللە /چارەسەرکاری دەروونی\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️ مامۆستا بوشرا حیدەر  /چارەسەرکاری دەروونی\n"
                         "07511817571☎️\n"
                         "🔻🔻🔻🔻🔻🔻🔻🔻🔻\n"
                         "✅دەوامی شەو\n"
                         "👨🏻‍⚕️دکتۆر ابراهیم اسکندر عبداللە / پسپۆڕی قورگ وگوێ و لوت\n"
                         "07511872525☎️\n"
                         "👨🏻‍⚕️ دکتۆر عیرفان احمد /پسپوڕی ســۆنــار\n"
                         "07511817571☎️\n"
                         "—————————————————-\n",
            "image": "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428374554_821685536638673_7167541847943829345_n.jpg"
        },

        '2': {
            "paragraph": "..............................................................................................................................."
                         "#خشتەی_دەوامی_کۆمەڵگەکەمان بۆ ڕۆژی #دوو_شەممە\n"
                         "12/2/2024\n"
                         "_______\n"
                         "✅دەوامی ڕۆژ\n"
                         "👨🏻‍⚕️دکتۆر هەردی لەتیف محی الدین/پسپۆری ئێسک و شکاوی\n"
                         "07511817571☎️\n"
                         "👩🏻‍⚕️ دکتۆرە سارە شاکر محمود /پسپۆڕی ژنان و مناڵبوون\n"
                         "07508036300 ☎️\n"
                         "👨🏻‍⚕️دکتۆر کمال عزیز عبدالقادر /پسپۆری نەشتەرگەری گشتی\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دکتۆر حسین عەلی ڕەمەزان /پسپۆری نەخۆشییەکانی چاو\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دکتۆر شوان ابوبکر /پسپۆری مێشک و دەمار\n"
                         "07508036300☎️\n"
                         "👩🏻‍⚕️ دکتۆرە ئایار عمر عەلی /پسپۆڕی جومگەو ڕۆماتیزم\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دکتۆر ابراهیم اسکندر عبداللە /پسپۆری قوڕگ و گوێ و لوت\n"
                         "07511872525☎️\n"
                         "🔻🔻🔻🔻🔻🔻🔻🔻🔻\n"
                         "✅دەوامی شەو\n"
                         "👩🏻‍⚕️ دکتۆرە هەرمان سیروان /پزیشکی گشتی\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دکتۆر حسین عەلی ڕەمەزان /پسپۆری نەخۆشییەکانی چاو\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دکتۆر فەرهەنگ محی الدین / پسپۆڕی تیشک و سۆنار\n"
                         "07511817571☎️\n"
                         "—————————————————\n",
            "image": "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428437753_822291419911418_222705539104554980_n.jpg"
        },

        '3': {
            "paragraph": "..............................................................................................................................."
                         "خشتەی_دەوامی_کۆمەڵگەکەمان بۆ ڕۆژی #سێ_شەممە\n"
                         "13/2/2024\n"
                         "___\n"
                         "✅دەوامی ڕۆژ\n"
                         "👨🏻‍⚕️دکتۆر ڕێباز ابراهیم احمد / پسپۆڕی گورچیلە و میزەڕۆ\n"
                         "07511817571 ☎️\n"
                         "👨🏻‍⚕️ دکتۆر کمال عزیز عبدالقادر / پسپۆڕی نەشتەرگەری گشتی\n"
                         "07511817571 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە پەیمان احمد کوێخا / پسپۆری پێست و لەیزەر\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️دکتۆر ڕەوەند حمەعلی هەڵەبجەیی / پسپۆڕی ئێسک و شکاوی\n"
                         "07511817571 ☎️\n"
                         "🔻🔻🔻🔻🔻🔻🔻🔻🔻\n"
                         "✅دەوامی شەو\n"
                         "👩🏻‍⚕️ دکتۆرە هەرمان سیروان /پزیشکی گشتی\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️ دکتۆر عیرفان احمد /پسپۆڕی ســـۆنـــار\n"
                         "07511817571 ☎️\n"
                         "————————\n",
            "image": "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428337079_818410726966154_8558263521344615809_n.jpg"
        },

        '4': {
            "paragraph": "..............................................................................................................................."
                         "#خشتەی_دەوامی_کۆمەڵگەکەمان بۆ ڕۆژی #چوار_شەممە\n"
                         "14/2/2024\n"
                         "___\n"
                         "✅دەوامی ڕۆژ\n"
                         "👩🏻‍⚕️دکتۆرە گوڵان عبداللە محمد / پسپۆری منداڵان و تازەلەدایک بووان\n"
                         "07511817571 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە سارە شاکر محمود / پسپۆری ژنان ومنداڵبوون\n"
                         "07508036300 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە پەیمان احمد کوێخا  / پسپۆری پێست و لەیزەر\n"
                         "07511872424 ☎️\n"
                         "👨🏻‍⚕️دکتۆر کمال عزیز عبدالقادر / پسپۆری نەشتەرگەری گشتی\n"
                         "07511817571 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە ئایار عمر عەلی / پسپۆری جومگەو ڕۆماتیزم\n"
                         "07511817571 ☎️\n"
                         "👨🏻‍⚕️دکتۆر ابراهیم اسکندر عبداللە / پسپۆڕی قوڕگ و گوێ و لوت\n"
                         "07511872552 ☎️\n"
                         "🔻🔻🔻🔻🔻🔻🔻🔻\n"
                         "✅دەوامی شەو\n"
                         "👩🏻‍⚕️دکتۆرە هەرمان سیروان محمود / پزیشکی گشتی\n"
                         "07511817571 ☎️\n"
                         "👨🏻‍⚕️دکتۆر فەرهەنگ محی الدین/ پسپۆڕی ســــۆنـــار\n"
                         "07511817571 ☎️\n"
                         "——————————\n",
            "image": "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428403939_819064163567477_2561860425728547661_n.jpg"
        },

        '5': {
            "paragraph": "..............................................................................................................................."
                         "#خشتەی_دەوامی_کۆمەڵگەکەمان بۆ ڕۆژی #پێنج_شەممە\n"
                         "15/2/2024\n"
                         "_____________\n"
                         "✅دەوامی ڕۆژ\n"
                         "👨🏻‍⚕️ دکتۆر ئومێد حسن عزیز / پسپۆری منداڵان و تازەلەدایک بووان\n"
                         "07511817571 ☎️\n"
                         "👨🏻‍⚕️ دکتۆر هاوژین شەماڵ ڕەمەزان / پسپۆری خۆراک و گەشە\n"
                         "07511817571 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە سارە شاکر محمود / پسپۆڕی ژنان و منداڵبوون\n"
                         "07508036300☎️\n"
                         "👨🏻‍⚕️ دکتۆر ڕێباز ابراهیم احمد / پسپۆری گورچیلەو میزەڕۆ\n"
                         "07511817571 ☎️\n"
                         "👨🏻‍⚕️ دکتۆر کمال عزیز عبدالقادر / پسپۆری نەشتەرگەری گشتی\n"
                         "07511817571 ☎️\n"
                         "🔻🔻🔻🔻🔻🔻🔻🔻🔻\n"
                         "✅دەوامی شەو\n"
                         "👩🏻‍⚕️دکتۆرە هەرمان سیروان / پزیشکی گشتی\n"
                         "07511817571☎️\n"
                         "👨🏻‍⚕️ دکتۆر عماد جلال حبیب اللە/ پسپۆری قوڕگ و گوێ و لوت\n"
                         "07511817571 ☎️\n"
                         "👩🏻‍⚕️دکتۆرە فێنک عبداللە حمەصالح / پسپۆڕی ســــۆنـــار\n"
                         "07511817571☎️\n"
                         "__\n",
            "image": "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\428405417_819800980160462_6619551575354013690_n.jpg"
        },

        '6': {
            "paragraph": "..............................................................................................................................."
                         "🟣 ڕۆژانی هەینی ئەم بەش و کلینیکانەی خوارەوە لە کۆمەڵگەکەمان کراوەن و لەخزمەت چارەخوازانی خۆشەویست دەبن:\n"
                         "‎🔸دەرمانخانە \n⏰کاتژمێر (2:00 تا 11:00)کراوەیە\n"
                         "‎🔸تاقیگە \n⏰کاتژمێر (2:00 تا 11:00)کراوەیە \n"
                         "‎🔸پەرستاری \n⏰کاتژمێر (2:00 تا 11:00)کراوەیە\n"
                         "‎🔸بەشی لەیزەر \nکاتژمێر (2:00 تا 6:00)کراوەیە⏰\n"
                         "‎🔸بەشی تیشک(الاشعە) \nکاتژمێر (2:00 تا 6:00)کراوەیە⏰\n\n"
                         "👩🏻‍⚕️د.فێنک عبداللە حمەصالح /پسپۆڕی سۆنار \n⏰ڕۆژانی هەینی\n\n"
                         "👩🏻‍⚕️د.دێکان محمود فتاح /پزیشکی گشتی \n⏰شەوانی هەینی\n",
            "image": "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\426620413_820885340052026_2564624572380563765_n.jpg"
        },}
    if selected_day_info := day_info.get(day):
        paragraph = selected_day_info["paragraph"]
        image_file_id_or_url = selected_day_info["image"]

        # Split the caption into a brief part and detailed part
        brief_caption = f"{paragraph[:1020]}..."
        detailed_info = paragraph  # Send detailed info as a follow-up message

        keyboard = [

            [InlineKeyboardButton("گەڕانەوە⬅️", callback_data='back_to_submenu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        chat_id = query.message.chat_id
        message_id_to_delete = query.message.message_id

        await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        # Send a new photo message with brief caption and option to get more details
        await context.bot.send_photo(chat_id=chat_id, photo=image_file_id_or_url, caption=brief_caption,
                                     reply_markup=reply_markup)






async def show_doctors_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        submenu_text = "سەرجەم دکتۆرەکانمان خاوەنی بڕوانامە و بۆردی تایبەتن بە نەخۆشیەکان🩺  \n\n\n\n"  "  🏨کۆمەڵگەی پزیشکی بەخشین "" لای  ئێمە دڵنیاتری 🎀 \n"""
        keyboard = [
            [InlineKeyboardButton("  پسپۆڕی: قوڕگ و گوێ و لوت👂🏻👃🏻", callback_data='da')],
            [InlineKeyboardButton("  پسپۆڕی: خۆراک و گەشە🥦🧍", callback_data='db')],
            [InlineKeyboardButton("  پسپۆڕی: نەخۆشیەکانی منداڵان👼🏻", callback_data='dc')],
            [InlineKeyboardButton("🩼پسپۆڕی: ئێسک و شکاوی", callback_data='dd')],
            [InlineKeyboardButton("پسپۆڕی: پێست و لەیزەرو جوانکاری💆🏻‍♀️ ", callback_data='de')],
            [InlineKeyboardButton("  پسپۆڕی: مێشک و دەمار 🧠", callback_data='df')],
            [InlineKeyboardButton("  پسپۆڕی: نەخۆشییە دەرونییەکان🤦🏻", callback_data='dg')],
            [InlineKeyboardButton("پسپۆڕی: نەخۆشییەکانی ژنان و منداڵ بوون 🤰🏻  ", callback_data='dh')],
            [InlineKeyboardButton(" پسپۆڕی: نەشتەرگەری گشتی 🩺", callback_data='di')],
            [InlineKeyboardButton("  پسپۆڕی: ددان  🦷 ", callback_data='dj')],
            [InlineKeyboardButton(" پسپۆڕی: گورچیلە و میزەڕۆ /نەزۆکی پیاوان 🚱 ", callback_data='dk')],
            [InlineKeyboardButton(" پسپۆڕی: جومگەو  ڕۆماتیزم و فەقەرات 🚶🏻 ", callback_data='dl')],
            [InlineKeyboardButton(" پسپۆڕی: نەشتەرگەری و نەخۆشیییەکانی چاو 👁 ", callback_data='dm')],
            [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=submenu_text, reply_markup=reply_markup)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        submenu_text = "ناونوسین بۆ بینینی پزیشک   .  .  .  .  .  .  .  .  .  .  .  🩺  \n\n\n\n"  "  🏨کۆمەڵگەی پزیشکی بەخشین "" لای  ئێمە دڵنیاتری 🎀 \n"""
        keyboard = [
            [InlineKeyboardButton(" 👨🏻‍⚕️دکتۆر عماد جلال حبیب اللە👂🏻👃🏻", callback_data='r1')],
            [InlineKeyboardButton(" 👨🏻‍⚕️دکتۆر ھاوژین شەماڵ ڕەمەزان🥦🧍", callback_data='r2')],
            [InlineKeyboardButton("  👩🏻‍⚕️دکتۆرە گوڵان عبداللە محمد👼🏻", callback_data='r3')],
            [InlineKeyboardButton("👨🏻‍⚕️دکتۆر ئومێد حسن عزیز👼🏻", callback_data='r4')],
            [InlineKeyboardButton("👨🏻‍⚕️دکتۆر ڕەوەند حمەعلی هەڵەبجەیی🩼 ", callback_data='r5')],
            [InlineKeyboardButton("  👨🏻‍⚕️دکتۆر هەردی لطیف محی الدین🩼", callback_data='r6')],
            [InlineKeyboardButton(" 👩🏻‍⚕️دکتۆرە پەیمان احمد کوێخا💆🏻‍♀️", callback_data='r7')],
            [InlineKeyboardButton("👨🏻‍⚕️دکتۆر شوان ابوبکر احمد🧠 ", callback_data='r8')],
            [InlineKeyboardButton(" 👨🏻‍⚕️ دکتۆر ماکوان محمد عبدالکریم🤦🏻", callback_data='r9')],
            [InlineKeyboardButton(" 👨🏻‍💼 به‌ڕێز محمد وەلی عبدالله🤦🏻 ", callback_data='r10')],
            [InlineKeyboardButton(" 👩🏻‍⚕️دکتۆرە سارە شاکر محمود🤰🏻  ", callback_data='r11')],
            [InlineKeyboardButton(" 👨🏻‍⚕️دکتۆر کمال عزیز عبدالقادر 🩺", callback_data='r12')],
            [InlineKeyboardButton(" 👨🏻‍⚕️دکتۆر صباح نصرالدين🦷", callback_data='r13')],
            [InlineKeyboardButton(" 👨🏻‍⚕️دکتۆر ڕێباز ابراهیم احمد🚱 ", callback_data='r14')],
            [InlineKeyboardButton(" 🧑🏻‍⚕️دکتۆرە ئایار عمر عەلی🚶🏻 ", callback_data='r15')],
            [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=submenu_text, reply_markup=reply_markup)



#...................................................................................

async def Start_Health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    submenu_text = "بەشداربە لەوەرگرتنی  چەندین زانیاری تەندرەستی ڕۆژانە بۆ ئێوەی  ئازیز      💊 🎁""\n\n\n""دەتەوێت بەشداربیت . . . . . ؟"
    keyboard = [
        [InlineKeyboardButton("بەڵی", callback_data='subscribe'),
        InlineKeyboardButton("نەخێر", callback_data='unsubscribe')],
        # Include other buttons as needed
        [InlineKeyboardButton("گەڕانەوە ⬅️", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=submenu_text, reply_markup=reply_markup)

    # Assuming you already have the handle_subscription_callback function
async def subscribe_user(user_id, query, context):
    if db := connect_to_db():
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO subscriptions (user_id, subscribed) VALUES (%s, TRUE) ON DUPLICATE KEY UPDATE subscribed = TRUE",
            (user_id,))
        db.commit()
        cursor.close()
        db.close()
        await query.edit_message_text("""   بەشداریت کرد لەوەرگرتنی  زانیاری تەندرەستی ڕۆژانە✅
        
        بەهیوای تەندرووستی باش💚""")
    else:
        await query.edit_message_text("ببورە کێشەیەک هەیە بە زووترین کات چارەسەردەکرێت")

async def unsubscribe_user(user_id, query, context):
    if db := connect_to_db():
        cursor = db.cursor()
        cursor.execute("UPDATE subscriptions SET subscribed = FALSE WHERE user_id = %s", (user_id,))
        db.commit()
        cursor.close()
        db.close()
        await query.edit_message_text("بەشداریت کرد لەوەرگرتنی  زانیاری تەندرەستی ڕۆژانە هەڵوەشاندەوە❌")
    else:
        await query.edit_message_text("ببورە کێشەیەک هەیە بە زووترین کات چارەسەردەکرێت")



# Assuming you have a function to send a message to a user by user_id
async def send_daily_health_tip(bot, health_tip_text, health_tip_photo_url):
    if db := connect_to_db():
        cursor = db.cursor()
        cursor.execute("SELECT user_id FROM subscriptions WHERE subscribed = TRUE")
        subscribed_users = cursor.fetchall()

        for user_id_tuple in subscribed_users:
            user_id = user_id_tuple[0]  # Extract the user_id from the tuple
            try:
                # Make sure health_tip_text is a string
                await bot.send_photo(chat_id=user_id, photo=health_tip_photo_url, caption=str(health_tip_text))
                await asyncio.sleep(0.1)
            except telegram.error.BadRequest as e:
                print(f"Failed to send message to {user_id}: {e.message}")
                # Handle the error (e.g., remove the user from the subscription list)

        cursor.close()
        db.close()


# Scheduler setup
def run_scheduler(bot):
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()

    async def schedule_health_tip_1():
        health_tip_text_1 = ("📌سودەکانی خواردنی سێو ""\n""\n""✅سێو دەتوانێت لە نەخۆشیەکانی دڵت بتپارێزێت" "\n" "✅خواردنی  سێو  یارمەتی کەمکردنەوەی کۆلیسترۆڵ دەدات""\n"
          "✅دەتپارێزێت لە نەخۆشی شێرپەنجە" "\n""✅یارمەتی تووشبووانی تەنگەنەفەسی دەدات""\n"" ✅پارێزگاری لە ئێسکەکان دەکات"
          )
        health_tip_photo_url_1 = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\benefits-of-apples-woman-biting-apple.jpg"
        await send_daily_health_tip(bot, health_tip_text_1, health_tip_photo_url_1)

    async def schedule_health_tip_2():
        health_tip_text_2 =( "📌سودەکانی خورما لە مانگی رەمەزاندا""\n""\n"" ✅بە سودە بۆ چارەسەركردنی نەخۆشییەكانی پەستانی خوێن و نەخۆشییەكانی دڵ""\n"
            "✅خواردنی ماست لەگەڵ خورما باشترین چارەسەرە بۆ لاوازی هەرسكردن و كێشەكانی كۆئەندامی هەرس""\n" "✅بە خێرا هێزی لەش چالاكتر دەكات و دەبێتە هۆی ڕێكخستنی ڕێژەی میز" "\n"
            "✅هاندەرە بۆ شوشتنی گورچیلە و دەبێتە هۆی پاككردنەوەی جگەر""\n" " ✅خورما پێكهاتووە لە ڤیتامینی A بە ڕێژەیەكی زۆر كە دەبێتە هۆی بەهێزكردنی بینین و پاراستنی چاو لە لاوازی" "\n" 
                             " ✅خورما هۆکارە بۆ هێمن كردنی دەمارەكان (ئەعساب) و چالاككردنی ڕژێنی گلاندی دەرەقی و دەبێتە هۆی ئارامكردنی هەستی مرۆڤ"
           )
        health_tip_photo_url_2 = "C:\\Users\\dadya\\PycharmProjects\\medical\\image\\165201822original1.805410.3.jpg"
        await send_daily_health_tip(bot, health_tip_text_2, health_tip_photo_url_2)

    def job_1():
        loop.run_until_complete(schedule_health_tip_1())

    def job_2():
        loop.run_until_complete(schedule_health_tip_2())

    # Schedule the first health tip
    schedule.every().day.at("00:58").do(job_1)
    # Schedule the second health tip
    schedule.every().day.at("01:00").do(job_2)

    while True:
        schedule.run_pending()
        time.sleep(1)








if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(conv_handler)
    app.add_handler(bale_handler)  # Add this line
    app.add_handler(PollAnswerHandler(handle_poll_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_feedback))
    scheduler_thread = Thread(target=run_scheduler, args=(app.bot,))
    scheduler_thread.start()
    app.run_polling()





