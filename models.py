from database import db


schedule_instructor_join_table = db.Table("schedule_instructor_join_table", db.metadata,
                                          db.Column("instructor_id", db.ForeignKey("instructor.id")),
                                          db.Column("schedule_id", db.ForeignKey("schedule.id")))


class Instructor(db.Model):
    __tablename__ = "instructor"
    id = db.Column(db.Integer, primary_key=True)
    instructor_type = db.Column(db.String(6))
    name = db.Column(db.Text)


class Schedule(db.Model):
    __tablename__ = "schedule"
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.Text)
    instructors = db.relationship("Instructor", secondary=schedule_instructor_join_table)
    days = db.Column(db.String(10))
    time = db.Column(db.String(15))
    class_id = db.Column(db.Integer, db.ForeignKey("class.class_number"))
    class_reference = db.relationship("Class", back_populates="schedules")


class Class(db.Model):
    __tablename__ = "class"
    course_id = db.Column(db.String(10), db.ForeignKey("course.code"))
    course = db.relationship("Course")
    class_section = db.Column(db.String(4))
    class_number = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    component = db.Column(db.Text)
    topics = db.Column(db.Text)
    term = db.Column(db.String(15))
    hours = db.Column(db.Float)
    meeting_dates = db.Column(db.String(15))
    instruction_type = db.Column(db.String)
    schedules = db.relationship("Schedule")
    enrollment_cap = db.Column(db.Integer)
    enrollment_total = db.Column(db.Integer)
    waitlist_cap = db.Column(db.Integer)
    waitlist_total = db.Column(db.Integer)
    min_enrollment = db.Column(db.Integer)
    attributes = db.Column(db.Text)
    combined_section_id = db.Column(db.Text)
    equivalents = db.Column(db.Text)

    def get_timeslots(self):
        timeslots = []

        def convert_time(time_string):
            time_parts = time_string.strip().split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1].split(" ")[0])
            if "PM" in time_string:
                hours += 12
            return (hours - 8) * int(60/5) + int(minutes/5) + 2

        for schedule in self.schedules:
            days = schedule.schedule.split(" ")[0]
            times = schedule.schedule[schedule.schedule.index(" ")::].split("-")
            start_time = convert_time(times[0])
            end_time = convert_time(times[1])

            def get_day(days):
                day_names = ("TH", "M", "T", "W", "F")
                day_num = (4, 1, 2, 3, 5)
                for i in range(len(day_names)):
                    if days.startswith(day_names[i]):
                        return days.replace(day_names[i], ""), day_num[i]

            while len(days) > 0:
                result = get_day(days)
                days = result[0]
                timeslots.append({
                    "day": result[1] + 1,
                    "start_time": start_time,
                    "end_time": end_time
                })

        return timeslots


class Course(db.Model):
    __tablename__ = "course"
    code = db.Column(db.String(10), primary_key=True)
    catalog_number = db.Column(db.Integer)
    title = db.Column(db.Text)
    hours = db.Column(db.String(10))
    description = db.Column(db.Text)
    honorsdescription = db.Column(db.Text)
    attrs = db.Column(db.Text)
    srcdb = db.Column(db.String(5))
