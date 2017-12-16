from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import *
from game.models import Location, LocationGroup, Activity


class LocationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    group_id = StringField("Group id")
    type = SelectField("Type", choices=Location.TYPES, coerce=int)
    description = StringField("Description", validators=[DataRequired()])

    def __init__(self, *args, obj=None, **kwargs):
        if obj is not None:
            if obj.group:
                kwargs["group_id"] = obj.group.id
        super().__init__(*args, obj=obj, **kwargs)

    def validate_group_id(self, field):
        if not field.data:
            return

        try:
            value = int(field.data)
        except ValueError:
            raise ValidationError("not int")
        try:
            LocationGroup.select().where(LocationGroup.id == value).get()
        except:
            raise ValidationError("group doesn't exists")

    def populate_obj(self, obj):
        obj.type = self.data["type"]
        obj.name = self.data["name"]
        obj.description = self.data["description"]
        if self.data["group_id"]:
            obj.group = LocationGroup.select().where(LocationGroup.id == int(self.data["group_id"]))
        else:
            obj.group = None


class LocationGroupForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    type = SelectField("Type", choices=LocationGroup.TYPES, coerce=int)
    description = StringField("Description", validators=[DataRequired()])

    def populate_obj(self, obj):
        obj.type = self.data["type"]
        obj.name = self.data["name"]
        obj.description = self.data["description"]


class ActivityForm(FlaskForm):
    type = SelectField("Type", choices=Activity.TYPES, coerce=int)
    duration = IntegerField("Duration")

    def populate_obj(self, obj):
        obj.type = self.data["type"]
        obj.duration = self.data["duration"]


class ItemForm(FlaskForm):
    type = IntegerField("Type")

    def populate_obj(self, obj):
        obj.type = self.data["type"]
