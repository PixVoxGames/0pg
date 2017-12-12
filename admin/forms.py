from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import *
from game.models import *


class LocationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    type = SelectField("Type", choices=Location.TYPES, coerce=int)
    description = StringField("Description", validators=[DataRequired()])

    def populate_obj(self, obj):
        obj.type = self.data["type"]
        obj.name = self.data["name"]
        obj.description = self.data["description"]


class LocationGroupForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    type = SelectField("Type", choices=LocationGroup.TYPES, coerce=int)
    description = StringField("Description", validators=[DataRequired()])

    def populate_obj(self, obj):
        obj.type = self.data["type"]
        obj.name = self.data["name"]
        obj.description = self.data["description"]
