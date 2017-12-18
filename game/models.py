import datetime
from enum import Enum, auto
from peewee import *
from playhouse.postgres_ext import BinaryJSONField
from conf import settings


class LocationGroup(Model):
    TOWN = 0
    DUNGEON = 1

    TYPES = (
        (TOWN, "TOWN"),
        (DUNGEON, "DUNGEON")
    )

    type = SmallIntegerField(choices=TYPES)
    name = CharField()
    description = TextField()

    class Meta:
        database = settings.DB


class Location(Model):
    START = 0
    EMPTY = 1
    FIGHT = 2
    HEALING = 3

    TYPES = (
        (START, "START"),
        (EMPTY, "EMPTY"),
        (FIGHT, "FIGHT"),
        (HEALING, "HEALING"),
    )

    type = SmallIntegerField(choices=TYPES)
    name = CharField()
    description = TextField()
    group = ForeignKeyField(LocationGroup, null=True, related_name="locations")
    is_enabled = BooleanField(default=False)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.name

    class Meta:
        database = settings.DB


class LocationGateway(Model):
    from_location = ForeignKeyField(Location, related_name="exits")
    to_location = ForeignKeyField(Location, related_name="entries")
    condition = BinaryJSONField()

    class Meta:
        database = settings.DB
        indexes = (
            (("from_location", "to_location"), True),
        )


class Activity(Model):
    RESPAWN = 0

    TYPES = (
        (RESPAWN, "RESPAWN"),
    )

    type = SmallIntegerField(choices=TYPES)
    start_time = DateTimeField(default=datetime.datetime.now)
    duration = IntegerField(default=0)

    class Meta:
        database = settings.DB


class HeroState(Model):
    name = CharField(unique=True)

    class Meta:
        database = settings.DB

class HeroStateTransition(Model):
    from_state = ForeignKeyField(HeroState, related_name="actions")
    to_state = ForeignKeyField(HeroState)

    class Meta:
        database = settings.DB
        indexes = (
            (("from_state", "to_state"), True),
        )

class Hero(Model):
    name = CharField(unique=True)
    state = ForeignKeyField(HeroState)
    activity = ForeignKeyField(Activity, null=True)
    location = ForeignKeyField(Location)
    gold = IntegerField(default=0)
    magic_exp = IntegerField(default=0)
    sword_exp = IntegerField(default=0)
    hp_base = FloatField(default=100)
    hp_value = FloatField(default=100)
    last_update = DateTimeField(default=datetime.datetime.now)

    user_id = IntegerField()
    registration_time = DateTimeField(default=datetime.datetime.now)
    last_message_at = DateTimeField(null=True)

    class Meta:
        database = settings.DB


class Mob(Model):
    name = CharField()
    location = ForeignKeyField(Location, related_name="mobs")
    hp = FloatField(constraints=[Check("hp > 0")])
    population = IntegerField(constraints=[Check("population > 0")])
    damage = IntegerField(constraints=[Check("damage > 0")])
    critical = IntegerField(constraints=[Check("critical > 0")])
    critical_chance = FloatField(constraints=[Check("critical_chance >= 0.0"),
                                                Check("critical_chance <= 1.0")])

    class Meta:
        database = settings.DB


class ItemPrototype(Model):
    DAMAGE = 0
    GUARD = 1
    HEAL = 2

    TYPES = (
        (DAMAGE, "DAMAGE"),
        (GUARD, "GUARD"),
        (HEAL, "HEAL"),
    )

    type = SmallIntegerField(choices=TYPES)
    title = CharField()
    value = IntegerField()
    usages = IntegerField(constraints=[Check("usages > 0")])
    price = IntegerField(constraints=[Check("price > 0")])
    dropped_by = ForeignKeyField(Mob, related_name="drops")
    drop_chance = FloatField(constraints=[Check("drop_chance > 0.0"),
                                                Check("drop_chance <= 1.0")])
    class Meta:
        database = settings.DB


class Item(Model):
    prototype = ForeignKeyField(ItemPrototype)
    owner = ForeignKeyField(Hero, related_name="items")
    usages_left = IntegerField(constraints=[Check("usages_left > 0")])
        #Check("usages_left <= prototype.usages")])

    class Meta:
        database = settings.DB


class Action(Model):
    MONEY = 0
    LOOT = 1
    FIGHT = 2

    TYPES = (
        (MONEY, "MONEY"),
        (LOOT, "LOOT"),
        (FIGHT, "FIGHT"),
    )
    receiver = ForeignKeyField(Hero)
    message = TextField()
    is_notified = BooleanField(default=False)

    class Meta:
        database = settings.DB


def create_db():
    with settings.DB.atomic():
        LocationGroup.create_table()
        Location.create_table()
        LocationGateway.create_table()
        Activity.create_table()
        HeroState.create_table()
        HeroStateTransition.create_table()
        Hero.create_table()
        Mob.create_table()
        ItemPrototype.create_table()
        Item.create_table()
        Action.create_table()

def create_hero_actions():
    with settings.DB.atomic():
        idle = HeroState.create(name="IDLE")
        travel = HeroState.create(name="TRAVEL")
        fight = HeroState.create(name="FIGHT")
        HeroStateTransition.create(from_state=idle, to_state=travel)
        HeroStateTransition.create(to_state=idle, from_state=travel)
        HeroStateTransition.create(from_state=idle, to_state=fight)
        HeroStateTransition.create(to_state=idle, from_state=fight)

def create_world():
    with settings.DB.atomic():
        Location.create(type=Location.START, name="The First Town",
                        description="Every adventure starts there.")
