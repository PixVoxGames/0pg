from envparse import env
from enum import Enum, auto
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters
from game.models import Hero, HeroState, Location
import locations.town
import locations.dungeon
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

env.read_envfile()


class State:
    REGISTER = auto()
    INTERNAL = auto()

def start(bot, update):
    update.message.reply_text(
        'Greetings, friend!\n\n'+
        'How would you like me to call you?')
    return State.REGISTER

def register(bot, update):
    update.message.reply_text(f'Welcome, {update.message.text}')
    hero = Hero.create(name=update.message.text, hp_base=100,
                location=Location.get(type=Location.START),
                user_id=update.effective_user.id,
                state=HeroState.get(name='IDLE'))
    actions(bot, update, hero)
    return State.INTERNAL

def actions(bot, update, hero):
    replies = ReplyKeyboardMarkup([[action.to_state.name for action in hero.state.actions]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("What's your path?",
                                reply_markup=replies)

def travel(bot, update):
    pass

def fight(bot, update):
    pass

def reactor(bot, update):
    try:
        hero = Hero.get(user_id=update.effective_user.id)
    except Hero.DoesNotExist:
        return start(bot, update)
    handlers[hero.state.name](bot, update, hero)
    return State.INTERNAL

handlers = {'IDLE': actions,
            'TRAVEL': travel,
            'FIGHT': fight}

updater = Updater(env("API_TOKEN"))
conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start)],
        states={
            #            **locations.town.handlers,
            # **locations.dungeon.handlers,
            State.REGISTER:[MessageHandler(Filters.text, register)],
            State.INTERNAL:[MessageHandler(Filters.text, reactor)]
            }, fallbacks=[])
updater.dispatcher.add_handler(conv_handler)
updater.dispatcher.add_handler(CommandHandler('actions', actions))
#updater.dispatcher.add_handler(MessageHandler(Filters.text, reactor))

updater.start_polling()
updater.idle()

