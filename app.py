from flask import render_template
from __init__ import app
from utilities import random_color
from database import db
from models import Class


@app.context_processor
def utility_processor():
    return dict(rand_color=random_color)


@app.route('/')
def schedule_viewer():
    classes = [db.session.query(Class).filter_by(class_number=1212).first(),
               db.session.query(Class).filter_by(class_number=1213).first(),
               db.session.query(Class).filter_by(class_number=1214).first()]

    return render_template("schedule.html", classes=classes)


if __name__ == '__main__':
    app.run()
