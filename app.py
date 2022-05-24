import json
import random
import uuid

from flask import render_template, Response, request
from __init__ import app
from database import db
from models import Class
from utilities import humanize_hour


@app.context_processor
def utility_processor():
    from utilities import generate_color, human_time
    return dict(generate_color=generate_color, human_time=human_time)


class Schedule:
    id = ""
    classes = []
    name = "Unnamed Schedule"
    def __init__(self, json_schedule):
        self.id = json_schedule["id"]
        self.name = json_schedule["name"]
        for class_number in json_schedule["class_numbers"]:
            self.classes.append(db.session.query(Class).filter_by(class_number=class_number).first())

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "class_numbers": [class_obj.class_number for class_obj in self.classes]
        }

    @classmethod
    def new(cls):
        return Schedule({
            "id": str(uuid.uuid4()),
            "name": "New Schedule",
            "class_numbers": []
        })


def get_active_schedule(request, response):
    if "schedules" in request.cookies:
        if "active_schedule" in request.cookies:
            return Schedule(json.loads(request.cookies.get("schedules")).get(request.cookies.get("active_schedule")))
        else:
            active_schedule = random.choice(request.cookies.get("schedules").keys())
            response.set_cookie("active_schedule", active_schedule)
            return Schedule(json.loads(request.cookies.get("schedules")).get(active_schedule))
    else:
        schedule = Schedule.new()
        schedules = {schedule.id: schedule.to_json()}
        response.set_cookie("schedules", value=json.dumps(schedules), secure=True)
        response.set_cookie("active_schedule", value=schedule.id, secure=True)
        return schedule


# TODO: accounts system to save schedules, watched classes, etc
# TODO: share schedule with friends to get a colored overlay
@app.route('/', methods=["GET"])
def schedule_viewer():
    response = Response()

    #schedule = get_active_schedule(request, response)

    response.data = render_template("schedule.html")

    return response


@app.route('/search', methods=["GET"])
def search():
    response = Response()

    schedule = get_active_schedule(request, response)

    response.data = render_template("search.html", schedule=schedule)
    return response


@app.route('/api/search', methods=["POST"])
# TODO: Search by name, professor, geneds
# TODO: Fade if class already in schedule
# TODO: Fade if class conflicts with schedule
def class_search():
    q = db.session.query(Class)
    if request.form.get("class_code") != "":
        q = q.filter(getattr(Class, "course_id").like("%%%s%%" % request.form.get("class_code")))
    if request.form.get("component") != "any":
        q = q.filter(getattr(Class, "component").like("%%%s%%" % request.form.get("component")))

    return render_template("search-result.html",
                           classes=q.order_by(Class.course_id, Class.class_section).limit(50).all())


@app.route('/api/schedule', methods=["POST", "OPTIONS"])
def schedule_maker():
    response_data = []
    for class_number in request.json["classNumbers"]:
        class_obj = db.session.query(Class).filter_by(class_number=class_number).first()
        if class_obj is None:
            print(f"Someone had an invalid class {class_number}")
            continue
        response_data.append({
            "parent": "#class-descriptions",
            "html": render_template("class_description.html", class_obj=class_obj)
        })
        for timeslot in class_obj.get_timeslots():
            response_data.append({
                "parent": f"#{timeslot['day']}",
                "html": render_template("class_slot.html", class_obj=class_obj, timeslot=timeslot)})
    return json.dumps(response_data)


app.jinja_env.globals.update(humanize_hour=humanize_hour)


if __name__ == '__main__':
    app.run()
