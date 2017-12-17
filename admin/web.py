import os
import datetime
from game.models import *
from .forms import *
from flask import Flask, g, request, session, redirect, Response
from flask.json import jsonify
from jinja2 import Environment, FileSystemLoader


_jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "templates"
    ))
)


def render(template, ctx={}):
    return _jinja_env.get_template(template).render(ctx)

app = Flask("0pg-admin", static_folder=os.path.join(os.path.dirname(os.path.realpath(__file__)), "static"))
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
    adj_id = request.args.get("adj")
    group_id = request.args.get("group")
    location = Location(state={})
    form = LocationForm(group_id=group_id)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(location)
        with settings.DB.atomic():
            if group_id:
                group = LocationGroup.select().where(LocationGroup.id == int(group_id))
                location.group = group
            location.save()
            if adj_id:
                adj_location = Location.select().where(Location.id == int(adj_id))
                LocationGateway.create(from_location=adj_location, to_location=location, condition={})
                LocationGateway.create(from_location=location, to_location=adj_location, condition={})
        return redirect(f"/locations/{location.id}")
    return render("locations/create.html", {
        "form": form,
        "adj_id": adj_id,
    })

@app.route("/locations/<int:lid>", methods=["GET", "POST"])
def locations_detail(lid):
    location = Location.select().where(Location.id == lid).get()
    adjacent = list(map(lambda x: x.to_location, location.exits))
    return render("locations/detail.html", {
        "location": location,
        "adjacent": adjacent,
    })

@app.route("/locations/<int:lid>/edit", methods=["GET", "POST"])
def locations_edit(lid):
    location = Location.select().where(Location.id == lid).get()
    form = LocationForm(obj=location)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(location)
        location.save()
        return redirect(f"/locations/{location.id}")
    return render("locations/edit.html", {
        "form": form
    })

@app.route("/groups/create", methods=["GET", "POST"])
def groups_create():
    group = LocationGroup(state={})
    form = LocationGroupForm()
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(group)
        group.save()
        return redirect(f"/groups/{group.id}")
    return render("groups/create.html", {
        "form": form,
    })

@app.route("/groups/")
def groups_index():
    groups = LocationGroup.select()
    return render("groups/index.html", {
        "groups": groups,
        "form": form,
    })

@app.route("/groups/<int:gid>", methods=["GET", "POST"])
def groups_detail(gid):
    group = LocationGroup.select().where(LocationGroup.id == gid).get()
    locations = Location.select().where(Location.group == group)
    edges = set()
    borders = set()

    def add_edge(edge, end):
        if edge:
            if end.group != group:
                borders.add(end)
            edges.add(tuple(sorted((edge.from_location.id, edge.to_location.id))))

    for loc in locations:
        for edge in LocationGateway.select().where(LocationGateway.from_location == loc):
            add_edge(edge, edge.to_location)
        for edge in LocationGateway.select().where(LocationGateway.to_location == loc):
            add_edge(edge, edge.from_location)

    return render("groups/detail.html", {
        "group": group,
        "locations": locations,
        "edges": edges,
        "borders": borders
    })

@app.route("/gateways/create", methods=["POST"])
def gateways_create():
    fr = int(request.form.get("from"))
    to = int(request.form.get("to"))
    from_location = Location.select().where(Location.id == fr).first()
    to_location = Location.select().where(Location.id == to).first()
    if from_location and to_location:
        LocationGateway.create(from_location=from_location, to_location=to_location, condition={})
        LocationGateway.create(from_location=to_location, to_location=from_location, condition={})
    return jsonify({})


@app.route("/gateways/delete", methods=["POST"])
def gateways_delete():
    fr = int(request.form.get("from"))
    to = int(request.form.get("to"))
    from_location = Location.select().where(Location.id == fr).first()
    to_location = Location.select().where(Location.id == to).first()
    if from_location and to_location:
        LocationGateway.delete().where(
            (LocationGateway.from_location == from_location) & (LocationGateway.to_location == to_location)
        ).execute()
        LocationGateway.delete().where(
            (LocationGateway.from_location == to_location) & (LocationGateway.to_location == from_location)
        ).execute()
    return jsonify({})


@app.route("/heroes/")
def heroes_index():
    return render("heroes/index.html", {
        "heroes": Hero.select()
    })


@app.route("/heroes/<int:hid>")
def heroes_detail(hid):
    return render("heroes/detail.html", {
        "hero": Hero.select().where(Hero.id == hid).first(),
        "now": datetime.datetime.now(),
        "types_dict": dict(Activity.TYPES)
    })


@app.route("/heroes/<int:hid>/add-item", methods=["GET", "POST"])
def heroes_add_item(hid):
    hero = Hero.select().where(Hero.id == hid).get()
    form = ItemForm()
    item = Item(owner=hero)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(item)
        item.save()
        return redirect(f"/heroes/{hero.id}")
    return render("heroes/add-item.html", {
        "form": form
    })


@app.route("/heroes/<int:hid>/new-activity", methods=["GET", "POST"])
def heroes_new_activity(hid):
    hero = Hero.select().where(Hero.id == hid).get()
    form = ActivityForm()
    activity = Activity()
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(activity)
        with settings.DB.atomic():
            if hero.activity:
                hero.activity.delete()
            activity.save()
            hero.activity = activity
            hero.save()
        return redirect(f"/heroes/{hero.id}")
    return render("heroes/new-activity.html", {
        "form": form
    })


@app.route("/items/<int:iid>", methods=["GET", "POST"])
def items_default(iid):
    item = Item.select().where(Item.id == iid).get()
    form = ItemForm(obj=item)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(item)
        item.save()
        return redirect(f"/items/{item.id}")
    return render("heroes/change-item.html", {
        "form": form
    })

def run_admin():
    app.run(host="0.0.0.0", port=1337, debug=True)
