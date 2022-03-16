from flask import Flask, render_template

from utilities import random_color

app = Flask(__name__)


@app.route('/')
def schedule_viewer():


    return render_template("schedule.html")


if __name__ == '__main__':
    app.run()
    app.jinja_env.globals.update(rand_color=random_color)
