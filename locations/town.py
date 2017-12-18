from enum import Enum, auto
from telegram.ext import RegexHandler, MessageHandler, Filters, CommandHandler
from telegram import ReplyKeyboardMarkup
from game.models import Hero, Location, LocationGateway

class State(Enum):
    MENU = auto()
    TRAVEL = auto()

def entry(bot, update):
    user_id = update.effective_user.id
    location = Hero.get(user_id=user_id).location
    update.message.reply_text(f"Welcome to the {location.name}!")
    return menu(bot, update)

def menu(bot, update):
    actions = ReplyKeyboardMarkup([["Travel"]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("What do you want to do?",
                                reply_markup=actions)

    return State.MENU

def travel(bot, update):
    user_id = update.effective_user.id
    paths = Hero.get(user_id=user_id).location.exits
    actions = ReplyKeyboardMarkup([[path.to_location.name for path in paths]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("Where do you want to go?",
                                reply_markup=actions)

    return State.TRAVEL

def travel_to(bot, update):
    user_id = update.effective_user.id
    hero = Hero.get(user_id=user_id)
    destination = update.message.text
    try:
        destination = Location.get(name=destination)
        source = hero.location
        LocationGateway.get(from_location=source, to_location=destination)
    except (Location.DoesNotExist, LocationGateway.DoesNotExist):
        update.message.reply_text(f"You can't travel to {destination} from here")
        return travel(bot, update)
    hero.update(location=destination).execute()
    return entry(bot, update)

from . import dungeon  # dirty hack to avoid circ. dep.

handlers = {State.MENU: [RegexHandler('^(Travel)$',
                            travel)],
            State.TRAVEL: [MessageHandler(Filters.text,
                           travel_to),
                           CommandHandler('cancel',
                            menu)]}
