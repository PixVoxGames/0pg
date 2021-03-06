import datetime
from enum import Enum, auto
from peewee import *
from playhouse.postgres_ext import BinaryJSONField
from playhouse.fields import ManyToManyField, DeferredThroughModel
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
    SHOP = 4

    TYPES = (
        (START, "START"),
        (EMPTY, "EMPTY"),
        (FIGHT, "FIGHT"),
        (HEALING, "HEALING"),
        (SHOP, "SHOP")
    )

    type = SmallIntegerField(choices=TYPES)
    name = CharField()
    description = TextField()
    group = ForeignKeyField(LocationGroup, null=True, related_name="locations")
    is_enabled = BooleanField(default=False)
    enter_price = IntegerField(default=0)

    def link_with(self, location):
        LocationGateway.create(from_location=self, to_location=location)
        LocationGateway.create(to_location=self, from_location=location)

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
    condition = BinaryJSONField(null=True)

    class Meta:
        database = settings.DB
        indexes = (
            (("from_location", "to_location"), True),
        )


class Activity(Model):
    RESPAWN = 0
    HEALING = 1

    TYPES = (
        (RESPAWN, "RESPAWN"),
        (RESPAWN, "HEALING"),
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

class Mob(Model):
    name = CharField()
    hp_base = IntegerField(constraints=[Check("hp_base > 0")])
    damage = IntegerField(constraints=[Check("damage > 0")])
    critical = IntegerField(constraints=[Check("critical > 0")])
    critical_chance = FloatField(constraints=[Check("critical_chance >= 0.0"),
                                                Check("critical_chance <= 1.0")])

    class Meta:
        database = settings.DB


class MobInstance(Model):
    type = ForeignKeyField(Mob)
    hp_value = IntegerField(constraints=[Check("hp_value > 0")])

    class Meta:
        database = settings.DB


class Hero(Model):
    name = CharField(unique=True)
    state = ForeignKeyField(HeroState)
    activity = ForeignKeyField(Activity, null=True)
    location = ForeignKeyField(Location)
    gold = IntegerField(default=100)
    xp_value = IntegerField(default=0)
    hp_base = IntegerField(default=100)
    hp_value = IntegerField(default=100)
    attacked_by = ForeignKeyField(MobInstance, null=True)
    last_update = DateTimeField(default=datetime.datetime.now)

    chat_id = IntegerField()
    registration_time = DateTimeField(default=datetime.datetime.now)
    last_message_at = DateTimeField(null=True)

    @property
    def level(self):
        return self.xp_value // 1000 + 1

    @property
    def respawn_time(self):
        return 5 + 5 * self.level

    def get_full_recover_time(self):
        return 15 * (self.hp_base - self.hp_value) / 5

    class Meta:
        database = settings.DB


class Item(Model):
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

    class Meta:
        database = settings.DB


class MobDwells(Model):
    location = ForeignKeyField(Location, related_name="dwellings")
    mob = ForeignKeyField(Mob, related_name="habitats")
    chance = FloatField(constraints=[
        Check("chance > 0.0"),
        Check("chance <= 1.0")
    ])

    class Meta:
        database = settings.DB


class MobDrops(Model):
    mob = ForeignKeyField(Mob, related_name="drops")
    item = ForeignKeyField(Item, related_name="dropped_by")
    chance = FloatField(constraints=[
        Check("chance > 0.0"),
        Check("chance <= 1.0")
    ])

    class Meta:
        database = settings.DB


class ItemInstance(Model):
    type = ForeignKeyField(Item)
    owner = ForeignKeyField(Hero, related_name="items")
    usages_left = IntegerField(constraints=[Check("usages_left > 0")])
        #Check("usages_left <= prototype.usages")])

    class Meta:
        database = settings.DB


class ShopSlot(Model):
    location = ForeignKeyField(Location, related_name="shop_slots")
    item = ForeignKeyField(Item)
    count = IntegerField(constraints=[Check("count >= 0")]) # warning: must be >=!
    price = IntegerField(constraints=[Check("price > 0")])

    class Meta:
        database = settings.DB
        primary_key = CompositeKey("location", "item")


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
        Mob.create_table()
        MobInstance.create_table()
        Hero.create_table()
        Item.create_table()
        ItemInstance.create_table()
        Action.create_table()
        ShopSlot.create_table()
        MobDwells.create_table()
        MobDrops.create_table()

def create_hero_actions():
    with settings.DB.atomic():
        idle = HeroState.create(name="IDLE")
        travel = HeroState.create(name="TRAVEL")
        fight = HeroState.create(name="FIGHT")
        HeroState.create(name="SHOPPING")
        HeroState.create(name="HEALING")
        HeroStateTransition.create(from_state=idle, to_state=travel)
        HeroStateTransition.create(to_state=idle, from_state=travel)
        HeroStateTransition.create(from_state=idle, to_state=fight)
        HeroStateTransition.create(to_state=idle, from_state=fight)

def create_world():
    with settings.DB.atomic():
        group = LocationGroup.create(name="The First Town", type=LocationGroup.TOWN, description="Every player starts here")
        first_city = Location.create(type=Location.START, name="Main Area",
                        description="Every adventure starts there.", group=group)
        cave = Location.create(type=Location.FIGHT, name="Goblin's Cave",
                        description="Small creatures lurk within.", group=group)
        shop = Location.create(type=Location.SHOP, name="Market",
                        description="A lot of people here...", group=group)
        tavern = Location.create(type=Location.HEALING, name="Tavern",
                        description="You can heal here", group=group)
        first_city.link_with(cave)
        first_city.link_with(shop)
        first_city.link_with(tavern)

        minotaur = Mob.create(name="Minotaur", damage=10, critical=30, critical_chance=0.3, hp_base=20)

        plain_sword = Item.create(type=Item.DAMAGE, title='Plain Sword',
                            value=30, usages=100, price=50)
        plain_shield = Item.create(type=Item.GUARD, title='Plain Shield',
                            value=20, usages=100, price=50)

        MobDrops.create(mob=minotaur, item=plain_sword, chance=0.7)
        MobDrops.create(mob=minotaur, item=plain_shield, chance=0.7)

        MobDwells.create(mob=minotaur, location=cave, chance=1)

        ShopSlot.create(location=shop, item=plain_shield, count=5, price=50)
        ShopSlot.create(location=shop, item=plain_sword, count=5, price=50)
