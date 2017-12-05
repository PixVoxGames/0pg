from envparse import env
from telegram.ext import Updater, ConversationHandler, CommandHandler

env.read_envfile()
# based on https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py
def start(bot, update):
    update.message.reply_text(
        'Greetings, friend!\n\n'
        'How would you like me to call you?')

    return ConversationHandler.END

updater = Updater(env("API_TOKEN"))
conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start)], states={}, fallbacks=[])
updater.dispatcher.add_handler(conv_handler)

updater.start_polling()
updater.idle()

