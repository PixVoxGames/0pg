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
    type = SmallIntegerField()
    start_time = DateTimeField()
    duration = IntegerField()

    class Meta:
        database = settings.DB


class FloatStat(Model):
    value = FloatField()
    base = FloatField()

    class Meta:
        database = settings.DB


class Hero(Model):
    name = CharField(unique=True)
    activity = ForeignKeyField(Activity, null=True)
    location = ForeignKeyField(Location)
    gold = IntegerField(default=0)
    magic_exp = IntegerField(default=0)
    sword_exp = IntegerField(default=0)
    hp_base = FloatField()
    hp_value = FloatField()
    mana_base = FloatField()
    mana_value = FloatField()
    last_update = DateTimeField()

    chat_id = IntegerField()
    registration_time = DateTimeField()
    last_message_at = DateTimeField()

    class Meta:
        database = settings.DB


class Mob(Model):
    name = CharField()
    type = SmallIntegerField()
    location = ForeignKeyField(Location)
    hp = FloatField()
    state = BinaryJSONField()

    class Meta:
        database = settings.DB


class Item(Model):
    type = SmallIntegerField()
    owner = ForeignKeyField(Hero)
    state = BinaryJSONField()

    class Meta:
        database = settings.DB


class Action(Model):
    receiver = ForeignKeyField(Hero)
    message = TextField()
    is_notified = BooleanField(default=False)

    class Meta:
        database = settings.DB


def create_db():
    LocationGroup.create_table()
    Location.create_table()
    LocationGateway.create_table()
    Activity.create_table()
    FloatStat.create_table()
    Hero.create_table()
    Mob.create_table()
    Item.create_table()
    Action.create_table()
