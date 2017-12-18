from envparse import env
from enum import Enum, auto
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters
from game.models import Hero, HeroState, HeroStateTransition, Location, LocationGateway
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
    return actions(bot, update, hero)

def actions(bot, update, hero):
    replies = ReplyKeyboardMarkup([[action.to_state.name for action in hero.state.actions]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("What's your path?",
                                reply_markup=replies)
    return State.INTERNAL

def handle_actions(bot, update, hero):
    query = update.message.text
    try:
        destination = HeroState.get(name=query)
        source = hero.state
        HeroStateTransition.get(from_state=source, to_state=destination)
    except (Location.DoesNotExist, LocationGateway.DoesNotExist):
        update.message.reply_text(f"You can't do {query} from here")
        return actions(bot, update, hero)
    hero.update(state=destination).execute()
    if query == 'TRAVEL':
        return travel(bot, update, hero)
    return State.INTERNAL


def travel(bot, update, hero):
    paths = hero.location.exits
    actions = ReplyKeyboardMarkup([[path.to_location.name for path in paths]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("Where do you want to go?",
                                reply_markup=actions)
    return State.INTERNAL

def handle_travel(bot, update, hero):
    destination = update.message.text
    try:
        destination = Location.get(name=destination)
        source = hero.location
        LocationGateway.get(from_location=source, to_location=destination)
    except (Location.DoesNotExist, LocationGateway.DoesNotExist):
        update.message.reply_text(f"You can't travel to {destination} from here")
        return travel(bot, update, hero)
    hero.location = destination
    hero.state = HeroState.get(name='IDLE')
    hero.save()
    return actions(bot, update, hero)

def fight(bot, update):
    pass

def reactor(bot, update):
    try:
        hero = Hero.get(user_id=update.effective_user.id)
    except Hero.DoesNotExist:
        return start(bot, update)
    handlers[hero.state.name](bot, update, hero)
    return State.INTERNAL

handlers = {'IDLE': handle_actions,
            'TRAVEL': handle_travel,
            'FIGHT': fight}

updater = Updater(env("API_TOKEN"))
conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start), MessageHandler(Filters.text, reactor)],
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

