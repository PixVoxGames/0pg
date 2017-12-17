from envparse import env
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler
import locations.town
import locations.dungeon
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

env.read_envfile()

def start(bot, update):
    update.message.reply_text(
        'Greetings, friend!')

    return locations.town.entry(bot, update)

updater = Updater(env("API_TOKEN"))
conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start)],
        states={**locations.town.handlers, **locations.dungeon.handlers}, fallbacks=[])
updater.dispatcher.add_handler(conv_handler)

updater.start_polling()
updater.idle()

