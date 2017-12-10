from envparse import env
from enum import Enum, auto
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters, RegexHandler

env.read_envfile()

class State(Enum):
    SETNAME = auto()
    MENU = auto()
    MENU_ACTION = auto()
    CHANGE_LOCATION = auto()

def start(bot, update):
    update.message.reply_text(
        'Greetings, friend!\n\n'
        'How would you like me to call you?')

    return State.SETNAME

def set_name(bot, update, user_data):
    user_data['name'] = update.message.text
    update.message.reply_text(
        f'Great, {update.message.text}! Now your adventure has begun!')
    return menu(bot, update, user_data)

def menu(bot, update, user_data):
    reply_keyboard = [['Go to', 'Inventory']]
    update.message.reply_text('Choose your path!',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
    return State.MENU_ACTION

def go_to(bot, update, user_data):
    reply_keyboard = [['City', 'Dungeon', 'Forest']]
    update.message.reply_text(f'Where would you like to go?',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
    return State.CHANGE_LOCATION

def change_location(bot, update, user_data):
    update.message.reply_text(f'You are now in {update.message.text}!')
    return menu(bot, update, user_data)

def show_inventory(bot, update, user_data):
    update.message.reply_text(f'Your inventory is empty as the soul of your ex...')
    return menu(bot, update, user_data)

updater = Updater(env("API_TOKEN"))
conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start)],
        states={
            State.SETNAME: [MessageHandler(Filters.text,
                                           set_name,
                                           pass_user_data=True),
                            ],
            State.MENU: [CommandHandler('menu',
                                           menu,
                                           pass_user_data=True),
                            ],
            State.MENU_ACTION: [RegexHandler("^(Go to)$",
                                           go_to,
                                           pass_user_data=True),
                                RegexHandler("^(Inventory)$",
                                           show_inventory,
                                           pass_user_data=True),

                            ],
            State.CHANGE_LOCATION: [MessageHandler(Filters.text,
                                           change_location,
                                           pass_user_data=True),
                            ]
        }, fallbacks=[])
updater.dispatcher.add_handler(conv_handler)

updater.start_polling()
updater.idle()

