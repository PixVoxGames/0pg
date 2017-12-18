from envparse import env
from enum import Enum, auto
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters
from game.models import Hero, HeroState, HeroStateTransition, Location, LocationGateway
from game.models import Mob, MobInstance
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
    try:
        hero = Hero.get(chat_id=update.effective_chat.id)
    except Hero.DoesNotExist:
        update.message.reply_text(
            'Greetings, friend!\n\n'+
            'How would you like me to call you?')
        return State.REGISTER
    else:
        update.message.reply_text(f'You are alredy registered, {hero.name}')
        return State.INTERNAL

def register(bot, update, job_queue):
    update.message.reply_text(f'Welcome, {update.message.text}')
    hero = Hero.create(name=update.message.text, hp_base=100,
                location=Location.get(type=Location.START),
                chat_id=update.effective_chat.id,
                state=HeroState.get(name='IDLE'))
    actions(bot, update, hero, job_queue)
    return State.INTERNAL

available_actions = {Location.START: ["Travel"],
                        Location.FIGHT: ["Fight", "Leave"]}
def actions(bot, update, hero, job_queue):
    replies = ReplyKeyboardMarkup([available_actions[hero.location.type]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("What's your path?",
                                reply_markup=replies)

def handle_actions(bot, update, hero, job_queue):
    query = update.message.text
    if query not in available_actions[hero.location.type]:
        update.message.reply_text(f"You can't do {query} from here")
        return actions(bot, update, hero, job_queue)
    if query == 'Travel' or query == 'Leave':
        return travel(bot, update, hero, job_queue)
    elif query == 'Fight':
        return fight(bot, update, hero, job_queue)


def travel(bot, update, hero, job_queue):
    paths = hero.location.exits
    actions = ReplyKeyboardMarkup([[path.to_location.name for path in paths]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("Where do you want to go?",
                                reply_markup=actions)
    hero.state = HeroState.get(name='TRAVEL')
    hero.save()

def handle_travel(bot, update, hero, job_queue):
    destination = update.message.text
    try:
        destination = Location.get(name=destination)
        source = hero.location
        LocationGateway.get(from_location=source, to_location=destination)
    except (Location.DoesNotExist, LocationGateway.DoesNotExist):
        update.message.reply_text(f"You can't travel to {destination} from here")
        return travel(bot, update, hero, job_queue)
    hero.location = destination
    hero.state = HeroState.get(name='IDLE')
    hero.save()
    if destination.type == Location.FIGHT:
        job_queue.run_once(fight, 10, context=hero.id)
    return actions(bot, update, hero, job_queue)

def fight(bot, job):
    hero = Hero.get(id=job.context)
    if hero.location.type != Location.FIGHT:
        return
    minotaur = Mob.get(name='Minotaur')
    mob = MobInstance.create(type=minotaur, hp=minotaur.hp)
    hero.state = HeroState.get(name='FIGHT')
    hero.attacked_by = mob
    hero.save()
    bot.send_message(chat_id=hero.chat_id,
                        text=f"You have encountered {mob.type.name}",
                        reply_markup=ReplyKeyboardMarkup([["Attack", "Guard", "Run away"]],
                        resize_keyboard=True))

def handle_fight(bot, update, hero, job_queue):
    action = update.message.text
    mob = hero.attacked_by
    if action == 'Attack':
        if mob.hp - 50 <= 0:
            update.message.reply_text(f"You killed {mob.type.name}")
            hero.state = HeroState.get(name='IDLE')
            hero.save()
            return actions(bot, update, hero, job_queue)
        mob.hp -= 50
        mob.save()
        update.message.reply_text(f"You hit {mob.type.name} with 50 dmg")
        hero.hp_value -= 10
        hero.save()
        update.message.reply_text(f"{mob.type.name} hits you with 10 dmg")
    elif action == 'Guard':
        hero.hp_value -= 5
        hero.save()
        update.message.reply_text(f"{mob.type.name} hits you with 5 dmg")
    elif action == 'Run away':
        update.message.reply_text("You ran in fear.")
        hero.state = HeroState.get(name='IDLE')
        hero.attacked_by = None
        hero.save()
        mob.delete_instance()
        return
    else:
        update.message.reply_text(f"Can't {action} now")

def reactor(bot, update, job_queue):
    try:
        hero = Hero.get(chat_id=update.effective_chat.id)
    except Hero.DoesNotExist:
        return start(bot, update)
    handlers[hero.state.name](bot, update, hero, job_queue)
    return State.INTERNAL

handlers = {'IDLE': handle_actions,
            'TRAVEL': handle_travel,
            'FIGHT': handle_fight}

updater = Updater(env("API_TOKEN"))
conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start),
                MessageHandler(Filters.text, reactor, pass_job_queue=True)],
        states={
            State.REGISTER:[MessageHandler(Filters.text, register, pass_job_queue=True)],
            State.INTERNAL:[MessageHandler(Filters.text, reactor, pass_job_queue=True)]
            }, fallbacks=[])
updater.dispatcher.add_handler(conv_handler)
#updater.dispatcher.add_handler(CommandHandler('actions', actions))
#updater.dispatcher.add_handler(MessageHandler(Filters.text, reactor))

updater.start_polling()
updater.idle()

