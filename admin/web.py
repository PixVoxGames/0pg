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
    adj_id = request.args.get("adj")
    group_id = request.args.get("group")
    location = Location(state={})
    form = LocationForm()
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
        "group_id": group_id,
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
        edge = LocationGateway.select().where(LocationGateway.from_location == loc).first()
        add_edge(edge, edge.to_location)
        edge = LocationGateway.select().where(LocationGateway.to_location == loc).first()
        add_edge(edge, edge.from_location)

    return render("groups/detail.html", {
        "group": group,
        "locations": locations,
        "edges": edges,
        "borders": borders
    })

def run_admin():
    app.run(host="0.0.0.0", port=1337)
