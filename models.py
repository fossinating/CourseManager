from database import db


schedule_instructor_join_table = db.Table("schedule_instructor_join_table", db.metadata,
                                          db.Column("instructor_id", db.ForeignKey("instructor.id")),
                                          db.Column("schedule_id", db.ForeignKey("schedule.id")))


class Instructor(db.Model):
    __tablename__ = "instructor"
    id = db.Column(db.Integer, primary_key=True)
    instructor_type = db.Column(db.String(6))
    name = db.Column(db.Text)


class Class(db.Model):
    __tablename__ = "class"
    course_id = db.Column(db.String(10), db.ForeignKey("course.code"))
    course = db.relationship("Course")
    class_section = db.Column(db.String(4))
    class_number = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    component = db.Column(db.Text)
    topics = db.Column(db.Text)
    term = db.Column(db.Integer, primary_key=True)
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
            return (hours - 8) * int(60/5) + int(minutes/5) + 2

        for schedule in self.schedules:
            scheduled_days = []
            readable_days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
            days = ["M", "Tu", "W", "Th", "F"]
            for i in range(len(days)):
                if days[i] in schedule.days:
                    scheduled_days.append(readable_days[i])
            times = schedule.time.split("-")
            start_time = 140
            end_time = 146
            if len(times) == 2:
                start_time = convert_time(times[0])
                end_time = convert_time(times[1])

            for day in scheduled_days:
                timeslots.append({
                    "day": day,
                    "start_time": start_time,
                    "end_time": end_time,
                    "schedule": schedule
                })

        return timeslots


class Schedule(db.Model):
    __tablename__ = "schedule"
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.Text)
    instructors = db.relationship("Instructor", secondary=schedule_instructor_join_table)
    days = db.Column(db.String(10))
    time = db.Column(db.String(15))
    class_id = db.Column(db.Integer)
    term = db.Column(db.Integer)
    __table_args__ = (db.ForeignKeyConstraint([class_id, term], [Class.class_number, Class.term]),
                      {})
    class_reference = db.relationship("Class", back_populates="schedules", foreign_keys=[class_id, term])

    def instructors_string(self):
        return "; ".join([instructor.name for instructor in self.instructors])


class CourseAttribute(db.Model):
    __tablename__ = "course_attributes"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.Text)
    value = db.Column(db.Text)
    parent_course_code = db.Column(db.String(10), db.ForeignKey("course.code"))


class Course(db.Model):
    __tablename__ = "course"
    code = db.Column(db.String(10), primary_key=True)
    title = db.Column(db.Text)
    credits = db.Column(db.String(10))
    description = db.Column(db.Text)
    attrs = db.relationship("CourseAttribute")
    last_updated = db.Column(db.DateTime)
