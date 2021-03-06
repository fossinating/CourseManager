from database import db
from models import Schedule, Instructor


def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def generate_color(class_code):
    dept_value = sum([ord(character) for character in class_code.split()[0]])
    code_value = sum([ord(character) for character in class_code.split()[1]])

    return f"{(dept_value % 180) + (code_value / 600.0 * 360 * 20 % 180)},70%,80%,1"


def human_time(mil_time):
    if "TBA" in mil_time:
        return mil_time
    times = mil_time.split(" - ")
    human_times = []
    for time in times:
        hour = int(time[:2])
        minute = int(time[3:])
        if hour > 11:
            human_times.append(f"{(hour - 1) % 12 + 1}:{minute:02d}pm")
        else:
            human_times.append(f"{hour}:{minute:02d}am")
    return " - ".join(human_times)


def humanize_hour(hour):
    return f"{(hour - 1) % 12 + 1}{'pm' if hour >= 12 else 'am'}"


def get_or_create_instructor(name):
    instructor = db.session.query(Instructor).filter_by(name=name).first()
    if instructor is None:
        instructor = Instructor(
            name=name,
            instructor_type="??"
        )
    return instructor


def search_to_schedule(class_data, term):
    class_number = safe_cast(class_data["class number"], int, -1)

    # possible schedule values:

    # None
    # TTH 02:00 PM-03:15 PM

    if class_data["schedule"] == "None":
        days = "TBA"
        time = "TBA"
        instructors = [get_or_create_instructor("TBA")]
    else:
        # convoluted code since T = Tu and TH = Th
        o_days = ["M", "T", "W", "TH", "F"]
        t_days = ["M", "Tu", "W", "Th", "F"]
        order = [3, 0, 1, 2, 4]
        schedule_arr = [""] * 5
        orig_days = class_data["schedule"][:class_data["schedule"].find(" ")]
        for i in order:
            if o_days[i] in orig_days:
                orig_days = orig_days.replace(o_days[i], "")
                schedule_arr[i] = t_days[i]
        days = "".join(schedule_arr)

        # translates to 24hr
        def translate_time(src_time):
            nums = src_time.split(" ")[0].split(":")
            hour = int(nums[0])
            mins = int(nums[1])
            return f"{(hour + (12 if ('PM' in src_time and hour < 12) else 0)):02}:{mins:02}"

        # get the time
        # splits the scheduled time to get only the hh:mm PM-hh:mm PM section
        # splits that by - to get the start and end times, then joins them after translating to 24hr
        time = " - ".join([translate_time(src_time) for src_time in
                           class_data["schedule"][class_data["schedule"].find(" ") + 1:].split("-")])

        instructors = [get_or_create_instructor(class_data["instructor name"])]

    return Schedule(
        location=class_data["room"],
        class_id=class_number,
        days=days,
        time=time,
        instructors=instructors,
        term=term
    )
