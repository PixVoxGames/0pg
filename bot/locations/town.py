from enum import Enum, auto
from telegram.ext import RegexHandler
from telegram import ReplyKeyboardMarkup


class State(Enum):
    MENU = auto()

def entry(bot, update):
    update.message.reply_text("Welcome to the Town!")
    return menu(bot, update)

def menu(bot, update):
    actions = ReplyKeyboardMarkup([["Go in dungeon"]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("What do you want to do?",
                                reply_markup=actions)

    return State.MENU

from . import dungeon  # dirty hack to avoid circ. dep.

handlers = {State.MENU: [RegexHandler("^(Go in dungeon)$",
                           dungeon.entry)]}
