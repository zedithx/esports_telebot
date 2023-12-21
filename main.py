import os
import logging
from functools import wraps

import telegram
from telegram import Update, ReplyKeyboardRemove, ChatAction, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, Updater, CommandHandler, MessageHandler, Filters
import firebase_admin
from firebase_admin import db

PORT = int(os.environ.get('PORT', '8443'))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

"""initialising variables/bot"""
TOKEN = ''
bot = telegram.Bot(token=TOKEN)

# define no. of variables to be stored
NAME, STUDENT_ID, TELEGRAM_HANDLE, CONFIRMATION_BOOKING, SUBMIT, CONFIRMATION_CHANGE = range(6)

information_database = {}
booking_dict = {'1': "Sept 26 (7-830)", '2': "Sept 26 (830-10)", '3': "Oct 3 (7-830)",
                '4': "Oct 3 (830-10)", '5': "Oct 10 (7-830)", '6': "Oct 10 (830-10)",
                '7': "Oct 17 (7-830)", '8': "Oct 17 (830-10)"}

"""Initialising firebase creds"""
cred_obj = firebase_admin.credentials.Certificate('./creds.json')
default_app = firebase_admin.initialize_app(cred_obj, {
    'databaseURL': ''
})
ref = db.reference("/")


def send_typing_action(func):
    """Wrapper to show that bot is typing"""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context, *args, **kwargs)

    return command_func


@send_typing_action
def start(update: Update, _: CallbackContext):
    """Starts the conversation."""
    print(information_database)
    user = update.message.from_user
    userID = str(update.message.chat_id)
    reply_keyboard = [['1', '2', '3', '4', '5', '6', '7', '8']]
    information_database[userID] = []
    text_string = ""
    for i in range(1, 9):
        if ref.child(booking_dict[f"{i}"]).get():
            text_string += f'{i}: {booking_dict[f"{i}"]}(booked)\n'
        else:
            text_string += f'{i}: {booking_dict[f"{i}"]}\n'
    update.message.reply_text(
        "Thank you for using the Esports Booking Telegram Bot. \n\n"
        "You can only book one slot per user. "
        "Which slot would you like to book?\n\n" + text_string, reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    logger.info("User %s is voting", user.first_name)
    return NAME

@send_typing_action
def name(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    if ref.child(booking_dict[f"{update.message.text}"]).get():
        update.message.reply_text(
            f"That slot has been booked already.\n\n"
            f"Please try booking another slot. Thank you! :<\n\n",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        information_database[userID].append(booking_dict[update.message.text])
        user = update.message.from_user
        update.message.reply_text(
            f"You have chosen to book the nintendo switch session on {booking_dict[update.message.text]} . \n\n"
            f"We will need your name, telegram handle and student ID to confirm your booking \n\n"
            "Firstly, what is your name?", reply_markup=ReplyKeyboardRemove()
        )
        return STUDENT_ID

@send_typing_action
def student_id(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    information_database[userID].append(update.message.text)
    user = update.message.from_user
    update.message.reply_text(
        "What is your student id?", reply_markup=ReplyKeyboardRemove()
    )
    return TELEGRAM_HANDLE

@send_typing_action
def telegram_handle(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    information_database[userID].append(update.message.text)
    user = update.message.from_user
    update.message.reply_text(
        "What is your telegram handle?", reply_markup=ReplyKeyboardRemove()
    )
    return CONFIRMATION_BOOKING

@send_typing_action
def confirmation_booking(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    information_database[userID].append(update.message.text)
    update.message.reply_text('Please check your details before submitting.\n')
    update.message.reply_text(
        'Date being booked: ' + information_database[userID][0] + '\n'
        'Name: ' + information_database[userID][1] + '\n'
        'Student ID: ' + information_database[userID][2] + '\n'
        'Telegram Handle: ' + information_database[userID][3] + '\n')
    reply_keyboard = [['Yes', 'No']]
    update.message.reply_text('Are they correct? \n \n'
                              'Enter Yes or No.',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return SUBMIT

@send_typing_action
def submit(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    if update.message.text.lower() == "yes":
        ref.child(f"{information_database[userID][0]}").child(f"{userID}").update(
            {f"name": f'{information_database[userID][1]}'})
        ref.child(f"{information_database[userID][0]}").child(f"{userID}").update(
            {f"id": f'{information_database[userID][2]}'})
        ref.child(f"{information_database[userID][0]}").child(f"{userID}").update(
            {f"telegram": f'{information_database[userID][3]}'})
        update.message.reply_text("You have successful confirmed the booking. For any enquiries, do contact @zedithx "
                                  f"on Telegram. See you at the ROOTCove on {information_database[userID][0]}!")
        return ConversationHandler.END
    else:
        update.message.reply_text(
            'Booking has been cancelled. \n'
            'Please start the bot again and rebook if you wish to do so', reply_markup=ReplyKeyboardRemove())
        logger.info(f"{information_database=}")
        return ConversationHandler.END

@send_typing_action
def change_booking(update: Update, _: CallbackContext):

    return ConversationHandler.END

@send_typing_action
def confirmation_change(update: Update, _: CallbackContext):

    return ConversationHandler.END

@send_typing_action
def cancel(update: Update, _: CallbackContext):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        "We hope that you will eventually book a slot!", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


if __name__ == '__main__':
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Book slot
    start_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(Filters.regex('^[1-8]$'), name)],
            STUDENT_ID: [MessageHandler(Filters.regex("^[^/].*"), student_id)],
            TELEGRAM_HANDLE: [MessageHandler(Filters.regex("^[^/].*"), telegram_handle)],
            CONFIRMATION_BOOKING: [MessageHandler(Filters.regex("^[^/].*"), confirmation_booking)],
            SUBMIT: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), submit)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        run_async=True
    )

    # Change booking
    change_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("change", change_booking)],
        states={
            CONFIRMATION_CHANGE: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), confirmation_change)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        run_async=True
    )

    dispatcher.add_handler(start_conv_handler)
    dispatcher.add_handler(change_conv_handler)
    updater.start_polling()
    updater.idle()
