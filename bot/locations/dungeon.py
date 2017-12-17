from enum import Enum, auto
from telegram.ext import RegexHandler
from telegram import ReplyKeyboardMarkup

class State(Enum):
    MENU = auto()
    FIGHT = auto()

def entry(bot, update):
    update.message.reply_text("You are in dungeon now!")
    return menu(bot, update)

def menu(bot, update):
    actions = ReplyKeyboardMarkup([["Fight", "Go back to city"]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("Let's see what we can find there.",
                                reply_markup=actions)

    return State.MENU

def fight(bot, update, chat_data):
    actions = ReplyKeyboardMarkup([["Hit", "Run away"]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    if "enemy" not in chat_data.keys():
        chat_data["enemy"] = {"name": "Minotaur", "hp": 100}
        update.message.reply_text("You have encountered Minotaur!")
    update.message.reply_text("Your turn!",
                                reply_markup=actions)

    return State.FIGHT

def fight_hit(bot, update, chat_data):
    update.message.reply_text("You hit Minotaur with 50 dmg")
    update.message.reply_text("Minotaur hits you with 0 dmg")
    chat_data["enemy"]["hp"] -= 50    
    if chat_data["enemy"]["hp"] <= 0:
        update.message.reply_text("You have defeated Minotaur!")
        del chat_data["enemy"]
        return menu(bot, update)
    return fight(bot, update, chat_data)


def fight_run_away(bot, update, chat_data):
    update.message.reply_text("You run away in fear.")
    del chat_data["enemy"]
    return menu(bot, update)

from . import town  # dirty hack to avoid circ. dep.

handlers = {State.MENU: [RegexHandler("^(Go back to city)$",
                                           town.entry),
                            RegexHandler("^(Fight)$",
                                            fight,
                                            pass_chat_data=True)],
            State.FIGHT: [RegexHandler("^(Hit)$",
                                        fight_hit,
                                        pass_chat_data=True),
                            RegexHandler("^(Run away)$",
                                           fight_run_away,
                                           pass_chat_data=True)]}

