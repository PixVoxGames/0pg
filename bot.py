from envparse import env
from enum import Enum, auto
from functools import wraps
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters
from game.models import Hero, HeroState, HeroStateTransition, Location, LocationGateway
from game.models import Mob, MobInstance, ItemInstance, Activity, ShopSlot, Item
from peewee import IntegrityError
import logging
import random
import datetime

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
                                        'Register with /register %nickname% command')
            return
        else:
            return func(bot, update, hero, *args, **kwargs)
    return wrapped

def start(bot, update):
    try:
        hero = Hero.get(chat_id=update.effective_chat.id)
    except Hero.DoesNotExist:
        update.message.reply_text('You are not registered yet.\n'+
                                    'Register with /register %nickname% command')
    else:
        update.message.reply_text(f'Name: {hero.name}\nHP:{hero.hp_value}')

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

available_actions = {
    Location.START: ["Travel"],
    Location.FIGHT: ["Leave"],
    Location.SHOP: ["Shop", "Travel"],
}

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
    elif query == 'Shop':
        hero.state = HeroState.get(name='SHOPPING')
        hero.save()
        return shop_actions(bot, update, hero)


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

    new_location = None
    for dest in hero.location.exits:
        if dest.to_location.name == destination:
            new_location = dest.to_location
            break

    if new_location is None:
        update.message.reply_text(f"You can't travel to {destination} from here")
        return travel(bot, update, hero, job_queue)

    hero.location = new_location
    hero.state = HeroState.get(name='IDLE')
    hero.save()
    if hero.location.type == Location.FIGHT:
        job_queue.run_once(fight, 5, context=hero.id)
    return actions(bot, update, hero)

def revive(bot, job):
    hero = Hero.get(id=job.context)
    hero.hp_value = hero.hp_base
    activity = hero.activity
    hero.activity = None
    hero.save()
    activity.delete_instance()
    bot.send_message(chat_id=hero.chat_id, text="You are alive!")

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

def on_kill(bot, update, hero, mob, job_queue):
    update.message.reply_text(f"You killed {mob.type.name}")
    hero.state = HeroState.get(name='IDLE')
    hero.attacked_by = None
    hero.save()
    mob.delete_instance()
    for item in mob.type.drops:
        if random.random() < item.drop_chance:
            item_instance = ItemInstance.create(type=item,
                                                owner=hero,
                                                usages_left=item.usages)
            update.message.reply_text(f"You got {item.title}")
    job_queue.run_once(fight, 5, context=hero.id)
    actions(bot, update, hero)

def on_death(bot, update, hero, mob, job_queue):
    update.message.reply_text(f"You were killed by {mob.type.name}\nRespawn in 30 secs")
    hero.activity = Activity.create(type=Activity.RESPAWN, duration=30)
    hero.attacked_by = None
    hero.state = HeroState.get(name='IDLE')
    hero.save()
    mob.delete_instance()
    job_queue.run_once(revive, 30, context=hero.id)

def handle_fight(bot, update, hero, job_queue):
    action = update.message.text
    mob = hero.attacked_by
    if action == 'Attack':
        hero_dmg = hero.level * 10
        update.message.reply_text(f"You hit {mob.type.name} with {hero_dmg} dmg")
        if mob.hp - hero_dmg <= 0:
            return on_kill(bot, update, hero, mob, job_queue)
        mob.hp -= hero_dmg
        mob.save()

        if random.random() < mob.type.critical_chance:
            mob_dmg = mob.type.critical
        else:
            mob_dmg = mob.type.damage
        update.message.reply_text(f"{mob.type.name} hits you with {mob_dmg} dmg")
        if hero.hp_value - mob_dmg <= 0:
            return on_death(bot, update, hero, mob, job_queue)
        hero.hp_value -= mob_dmg
        hero.save()
    elif action == 'Guard':
        update.message.reply_text("You block next attack with a shield")
        if random.random() < mob.type.critical_chance:
            mob_dmg = mob.type.critical
        else:
            mob_dmg = mob.type.damage
        mob_dmg = max(0, mob_dmg - hero.level * 10)  # replace with shield def
        update.message.reply_text(f"{mob.type.name} hits you with {mob_dmg} dmg")
        if hero.hp_value - mob_dmg <= 0:
            return on_death(bot, update, hero, mob, job_queue)
        hero.hp_value -= mob_dmg
        hero.save()
    elif action == 'Run away':
        update.message.reply_text("You ran in fear.")
        hero.state = HeroState.get(name='IDLE')
        hero.attacked_by = None
        hero.save()
        mob.delete_instance()
        return actions(bot, update, hero)
    else:
        update.message.reply_text(f"Can't {action} now")


def shop_actions(bot, update, hero):
    actions = ReplyKeyboardMarkup(
        [
            [f"Buy '{slot.item.title}'" for slot in hero.location.shop_slots],
            ["Leave"]
        ],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    update.message.reply_text(
        f"You have {hero.gold} gold. What do you want?",
        reply_markup=actions
    )


def handle_shopping(bot, update, hero, job_queue):
    action = update.message.text.split(" ", 1)
    if len(action) == 1 and action[0].lower() == "leave":
        hero.state = HeroState.get(name="IDLE")
        hero.save()
        return actions(bot, update, hero)
    if len(action) != 2:
        update.message.reply_text("I didn't understood you")
        return shop_actions(bot, update, hero)

    action, request = action
    try:
        request = request[1:-1]
        requested_item = Item.get(title=request)
    except Item.DoesNotExist:
        update.message.reply_text(f"Cannot find item '{request}'")
    else:
        if action.lower() == "buy":
            updated = ShopSlot.update(count=ShopSlot.count - 1).where(
                (ShopSlot.count > 0) &
                (ShopSlot.item == requested_item)
            ).execute()
            if updated == 1:
                slot = ShopSlot.get(item=requested_item)
                updated = Hero.update(gold=Hero.gold - slot.price).where(
                    (Hero.id == hero.id) &
                    (Hero.gold >= slot.price)
                ).execute()
                if updated == 1:
                    item = ItemInstance.create(
                        type=requested_item,
                        owner=hero,
                        usages_left=requested_item.usages
                    )
                    update.message.reply_text(f"You bought '{item.type.title}'")
                    if slot.count == 0:
                        slot.delete_instance()
                    hero = Hero.get(id=hero.id)
                else:
                    update.message.reply_text(
                        f"You don't have enough money, you have: {hero.gold}, needed: {slot.price}"
                    )
                    ShopSlot.update(count=ShopSlot.count + 1).where(ShopSlot.id == slot.id).execute()
            else:
                update.message.reply_text(f"Shop has no item '{request}'")
        elif action.lower() == "sell":
            pass
        else:
            update.message.reply_text("I didn't understood you")
    return shop_actions(bot, update, hero)

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
    listing = '\n'.join([f"{item.type.title}" for item in items])
    if listing == '':
        update.message.reply_text('Your inventory is empty')
    else:
        update.message.reply_text(listing)

@registered
def reactor(bot, update, hero, job_queue):
    if hero.activity:
        if hero.activity.type == Activity.RESPAWN:
            remaining = (hero.activity.start_time + datetime.timedelta(seconds=hero.activity.duration)) - datetime.datetime.now()
            assert remaining.seconds >= 0
            update.message.reply_text(f"Your hero is dead. Respawn in {remaining.seconds} seconds")
    else:
        handlers[hero.state.name](bot, update, hero, job_queue)

handlers = {'IDLE': handle_actions,
            'TRAVEL': handle_travel,
            'FIGHT': handle_fight,
            'SHOPPING': handle_shopping}

updater = Updater(env("API_TOKEN"))

updater.dispatcher.add_handler(MessageHandler(Filters.text, reactor, pass_job_queue=True))
updater.dispatcher.add_handler(CommandHandler('register', register, pass_args=True, pass_job_queue=True))
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('cancel', cancel))
updater.dispatcher.add_handler(CommandHandler('inventory', show_inventory))

updater.start_polling()
updater.idle()

