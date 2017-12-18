from envparse import env
from enum import Enum, auto
from functools import wraps
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters
from game.models import Hero, HeroState, HeroStateTransition, Location, LocationGateway
from game.models import Mob, MobInstance
from peewee import IntegrityError
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
env.read_envfile()

def registered(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        try:
            hero = Hero.get(chat_id=update.effective_chat.id)
        except Hero.DoesNotExist:
            update.message.reply_text('You are not registered yet.\n'+
                                        'Register with `/register %nickname%` command')
            return
        else:
            return func(bot, update, hero, *args, **kwargs)
    return wrapped

def register(bot, update, args, job_queue):
    nickname = args[0]
    try:
        hero = Hero.create(name=nickname, hp_base=100,
                    location=Location.get(type=Location.START),
                    chat_id=update.effective_chat.id,
                    state=HeroState.get(name='IDLE'))
    except IntegrityError:
        update.message.reply_text(f'Nickname {nickname} already exists')
    else:
        update.message.reply_text(f'Welcome, {nickname}')
        actions(bot, update, hero)

available_actions = {Location.START: ["Travel"],
                        Location.FIGHT: ["Leave"]}

def actions(bot, update, hero):
    replies = ReplyKeyboardMarkup([available_actions[hero.location.type]],
                                    one_time_keyboard=True,
                                    resize_keyboard=True)
    update.message.reply_text("What's your path?",
                                reply_markup=replies)

def handle_actions(bot, update, hero, job_queue):
    query = update.message.text
    if query not in available_actions[hero.location.type]:
        update.message.reply_text(f"You can't do {query} from here")
        return actions(bot, update, hero)
    if query == 'Travel' or query == 'Leave':
        return travel(bot, update, hero, job_queue)


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
        job_queue.run_once(fight, 5, context=hero.id)
    return actions(bot, update, hero)

def fight(bot, job):
    hero = Hero.get(id=job.context)
    if hero.location.type != Location.FIGHT or hero.state.name =='FIGHT':
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
            return actions(bot, update, hero)
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

@registered
def cancel(bot, update, hero):
    if hero.state.name == 'IDLE':
        update.message.reply_text("There's nothing to cancel")
    elif hero.state.name == 'FIGHT':
        update.message.reply_text("Can't cancel a fight")
    elif hero.state.name == 'TRAVEL':
        hero.state = HeroState.get(name='IDLE')
        hero.save()
        return actions(bot, update, hero)


@registered
def show_inventory(bot, update, hero):
    items = Hero.get(chat_id=update.effective_chat.id).items
    listing = '\n'.join([f"{item.type.name}" for item in items])
    if listing == '':
        update.message.reply_text('Your inventory is empty')
    else:
        update.message.reply_text(listing)

@registered
def reactor(bot, update, hero, job_queue):
    handlers[hero.state.name](bot, update, hero, job_queue)

handlers = {'IDLE': handle_actions,
            'TRAVEL': handle_travel,
            'FIGHT': handle_fight}

updater = Updater(env("API_TOKEN"))

updater.dispatcher.add_handler(MessageHandler(Filters.text, reactor, pass_job_queue=True))
updater.dispatcher.add_handler(CommandHandler('register', register, pass_args=True, pass_job_queue=True))
updater.dispatcher.add_handler(CommandHandler('cancel', cancel))
updater.dispatcher.add_handler(CommandHandler('inventory', show_inventory))

updater.start_polling()
updater.idle()

