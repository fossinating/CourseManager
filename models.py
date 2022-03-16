from database import db


class Schedule(db.Model):
    __tablename__ = "class_schedules"
    id = db.Column(db.Integer, primary_key=True)
    schedule = db.Column(db.String(15))
    class_id = db.Column(db.Integer, db.ForeignKey("class.class_number"))
    class_reference = db.relationship("Class", back_populates="schedules")


class Class(db.Model):
    __tablename__ = "class"
    course_id = db.Column(db.String(10), db.ForeignKey("course.id"))
    course = db.relationship("Course")
    class_section = db.Column(db.String(4))
    class_number = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    term = db.Column(db.String(15))
    hours = db.Column(db.Float)
    meeting_dates = db.Column(db.String(15))
    schedules = db.relationship("Schedule")
    room = db.Column(db.String)
    instruction_type = db.Column(db.String)
    available_seats = db.Column(db.Integer)
    total_seats = db.Column(db.Integer)


class Course(db.Model):
    __tablename__ = "course"
    id = db.Column(db.String(10), primary_key=True)
    subject = db.Column(db.String(4))
    catalog_number = db.Column(db.String(5))
    same_as_id = db.Column(db.String(10))#, db.ForeignKey("course.id"))
    #same_as = db.relationship("course")
