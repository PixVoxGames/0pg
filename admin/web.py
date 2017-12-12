import os
from game.models import *
from .forms import *
from flask import Flask, g, request, session, redirect, Response
from jinja2 import Environment, FileSystemLoader


_jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "templates"
    ))
)


def render(template, ctx={}):
    return _jinja_env.get_template(template).render(ctx)

app = Flask("0pg-admin")
app.config["SESSION_COOKIE_SECRET_KEY"] = settings.SESSION_COOKIE_SECRET_KEY
app.config["SECRET_KEY"] = settings.SECRET_KEY
app.config["WTF_CSRF_ENABLED"] = False


@app.route("/")
def index():
    return render("index.html")


@app.route("/locations/")
def locations_index():
    locations = Location.select()
    return render("locations/index.html", {
        "locations": locations
    })

@app.route("/locations/create", methods=["GET", "POST"])
def locations_create():
    from_id = request.args.get("from")
    to_id = request.args.get("to")
    location = Location(state={})
    form = LocationForm()
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(location)
        location.save()
        if from_id:
            from_location = Location.select().where(Location.id == int(from_id))
            LocationGateway.create(from_location=from_location, to_location=location, condition={})
        if to_id:
            to_location = Location.select().where(Location.id == int(to_id))
            LocationGateway.create(from_location=location, to_location=to_location, condition={})
        return redirect(f"/locations/{location.id}")
    return render("locations/create.html", {
        "form": form,
        "from_location": from_id,
        "to_location": to_id
    })

@app.route("/locations/<int:lid>", methods=["GET", "POST"])
def locations_detail(lid):
    location = Location.select().where(Location.id == lid).get()
    exits = list(map(lambda x: x.to_location, location.exits))
    entries = list(map(lambda x: x.from_location, location.entries))
    return render("locations/detail.html", {
        "location": location,
        "exits": exits,
        "entries": entries,
    })

def run_admin():
    app.run(host="0.0.0.0", port=1337)
