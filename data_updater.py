import datetime
import os
import urllib.request

import requests as requests
from tqdm import tqdm
from bs4 import BeautifulSoup, NavigableString
from urllib3.exceptions import NewConnectionError, MaxRetryError
from tika import parser
from os.path import exists
import filecmp

from models import Course, Class, db, Schedule, Instructor, CourseAttribute


def get_root_text(html_element):
    if isinstance(html_element, NavigableString):
        return html_element
    elif len(html_element.contents) == 0:
        return ""
    else:
        return get_root_text(html_element.contents[0])


def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


subjects = (
    "AERO", "AAAD", "AMST", "ANTH", "APPL", "ARAB", "ARCH", "ARMY", "ARTH", "ASIA", "ASTR", "BIOC", "BCB", "BBSP",
    "BIOL",
    "BMME", "BIOS", "BCS", "BUSI", "CHIP", "CBIO", "CBPH", "CBMC", "CHEM", "CHER", "CHIN", "PLAN", "CLAR", "CLAS",
    "CLSC",
    "CRMH", "COMM", "CMPL", "COMP", "EURO", "CZCH", "DENG", "DHYG", "DHED", "DRAM", "DTCH", "ECON", "EDUC", "ENDO",
    "ENGL",
    "ENEC", "ENVR", "EPID", "EXSS", "EDMX", "DPET", "FOLK", "FREN", "GNET", "GEOL", "GEOG", "GERM", "GSLL", "GLBL",
    "GOVT",
    "GRAD", "GREK", "HBEH", "HPM", "HEBR", "HNUR", "HIST", "INLS", "IDST", "ITAL", "JAPN", "JWST", "SWAH", "KOR",
    "LTAM",
    "LATN", "LFIT", "LGLA", "LING", "MASC", "MTSC", "MHCH", "MATH", "MEJO", "MCRO", "MUSC", "NAVS", "NBIO", "NSCI",
    "NURS",
    "NUTR", "OCSC", "OCCT", "OPER", "ORPA", "ORAD", "ORTH", "PATH", "PWAD", "PEDO", "PERI", "PRSN", "PHRS", "DPMP",
    "PHCO",
    "PHCY", "DPOP", "PHIL", "PHYA", "PHYS", "PHYI", "PLSH", "POLI", "PORT", "PACE", "PROS", "PSYC", "PUBA", "PUBH",
    "PLCY",
    "RADI", "RECR", "RELI", "ROML", "RUSS", "SPHG", "SLAV", "SOWO", "SOCI", "SPAN", "SPHS", "STOR", "ARTS", "TOXC",
    "TURK",
    "WOLO", "WGST", "VIET")


def get_unc_course_data():
    for subject in tqdm(subjects, position=0, leave=False, desc="subjects"):
        subject_response = None
        while subject_response is None:
            try:
                subject_response = requests.post("https://catalog.unc.edu/course-search/api/index.cgi",
                                                 params={
                                                     "page": "fose",
                                                     "route": "search",
                                                     "keyword": subject
                                                 },
                                                 json={
                                                     "other": {"srcdb": ""},
                                                     "criteria": [
                                                         {"field": "keyword",
                                                          "value": subject}
                                                     ]
                                                 })
            except (ConnectionError, TimeoutError, NewConnectionError, MaxRetryError) as e:
                subject_response = None
                print(e)

        for course in tqdm(subject_response.json()["results"], position=1, leave=False, desc=subject):
            if db.session.query(Course.catalog_number).filter_by(catalog_number=course["key"],
                                                                 srcdb=course["srcdb"]).first() is None:
                course_response = None
                while course_response is None:
                    try:
                        course_response = requests.post("https://catalog.unc.edu/course-search/api/index.cgi",
                                                        params={
                                                            "page": "fose",
                                                            "route": "details"
                                                        },
                                                        json={
                                                            "group": f"key:{course['key']}",
                                                            "key": f"key:{course['key']}",
                                                            "srcdb": course["srcdb"],
                                                            "matched": f"key:{course['key']}"
                                                        })
                    except (ConnectionError, TimeoutError, NewConnectionError, MaxRetryError) as e:
                        course_response = None
                        print(e)

                course_data = course_response.json()

                if db.session.query(Course.code).filter_by(code=course_data["code"]).first() is None:
                    db.session.add(Course(
                        code=course_data["code"],
                        catalog_number=course_data["key"],
                        title=course_data["title"],
                        hours=course_data["hours"],
                        description=course_data["description"],
                        honorsdescription=course_data["honorsdesc"],
                        attrs=course_data["attrs"],
                        srcdb=course["srcdb"]
                    ))


def get_sections_data(terms):
    for term in terms:
        get_sections_data_for_term(term)


# gets information about classes from the class search
# (will not get information about any class without credit hours)
def get_sections_data_for_term(term):
    response = requests.get("https://reports.unc.edu/class-search/advanced_search/", params={
        "term": term,
        "advanced": ", ".join(subjects)
    })

    missing_courses = []
    missing_classes = []

    print("got a response")
    soup = BeautifulSoup(str(response.content).replace("\\n", ""), "html.parser")

    rows = soup.select("#results-table > tbody > tr")
    static_class_data = {}
    for row in tqdm(rows, position=0):
        class_data = {}
        i = 0
        while i < len(row.contents):
            key = row.contents[i].split(";")[0].strip()
            value = get_root_text(row.contents[i + 1])
            class_data[key] = value
            static_class_data[key] = value
            i += 2

        # check to see if the course exists, if not leave a warning
        course_id = static_class_data["subject"] + " " + static_class_data["catalog number"]
        if db.session.query(Course.code).filter_by(code=course_id).first() is None:
            missing_courses.append(course_id)
            db.session.add(Course(
                code=course_id,
                title=class_data["course description"],
                description="Generated from section data",
                credits=class_data["credit hours"]
            ))

        class_number = safe_cast(class_data["class number"], int, -1)

        class_obj = db.session.query(Class).filter_by(class_number=class_number, term=term).first()
        if class_obj is None:
            missing_classes.append(str(class_number))

            db.session.add(Schedule(
                location=class_data["room"],
                class_id=class_number,
                term=term
            ))

            db.session.add(Class(
                course_id=course_id,
                class_section=class_data["section number"],
                class_number=class_number,
                title=class_data["course description"],
                term=term,
                hours=safe_cast(class_data["credit hours"], float, -1.0),
                meeting_dates=class_data["meeting dates"],
                instruction_type=class_data["instruction mode"],
                enrollment_total=-1 * safe_cast(class_data["available seats"], int, -1)
            ))
        else:
            class_obj.meeting_dates = class_data["meeting dates"]
            class_obj.instruction_type = class_data["instruction mode"]
            class_obj.enrollment_total = \
                (0 if class_obj.enrollment_cap is None else class_obj.enrollment_cap) \
                - safe_cast(class_data["available seats"], int, -1)

    print(f"Created entries for {len(missing_courses)} missing courses: " + ",".join(missing_courses))
    print(f"Created entries for {len(missing_classes)} missing classes: " + ",".join(missing_classes))


def pdf_data(terms):
    print("Getting most up to date pdf")

    response = requests.get("https://registrar.unc.edu/courses/schedule-of-classes/directory-of-classes-2/")

    soup = BeautifulSoup(response.content, "html.parser")

    for link in soup.select("div > ul > li > a"):
        if link.text in terms:
            source = link["href"]
            term = source.split("/")[-1].split("-")[0]
            filename = "ssb-collection/" + term + ".pdf"
            temp_filename = "temp/" + term + ".pdf"
            if not exists("temp/"):
                os.mkdir("temp")
            if not exists("ssb-collection/"):
                os.mkdir("ssb-collection")
            if exists(temp_filename):
                os.remove(temp_filename)
            print(f"Downloading {filename} from {source}")
            urllib.request.urlretrieve(source, temp_filename)

            if not exists(filename) or not filecmp.cmp(filename, temp_filename):
                print("File changed, analysing new PDF")
                print(f"Deleted {db.session.query(Class).filter_by(term=term).delete()} classes from term {term}")
                print(f"Deleted {db.session.query(Schedule).filter_by(term=term).delete()} schedules from term {term}")
                if exists(filename):
                    os.remove(filename)
                os.rename(temp_filename, filename)
                get_data_from_pdf(filename)
            else:
                print(f"File unchanged")
                os.remove(temp_filename)


def get_data_from_pdf(file_name):
    print(f"Processing {file_name}")

    missing_courses = []

    term = file_name.split("/")[1].split(".")[0]
    raw = parser.from_file(file_name)
    class_data = {}
    for line in tqdm(raw["content"].strip().split("\n"), position=0):
        if line.strip() == "":
            continue
        if "_________________________________________________________________________________________________________" in line:
            if len(class_data) > 0:
                course_id = class_data["dept"] + " " + class_data["catalog_number"]
                # check to see if the course exists, if not leave a warning
                if db.session.query(Course.code).filter_by(code=course_id).first() is None:
                    missing_courses.append(course_id)
                    db.session.add(Course(
                        code=course_id,
                        title=class_data["title"],
                        credits=class_data["units"],
                        last_updated=datetime.datetime.utcnow()
                    ))

                schedules = []
                for schedule_data in class_data["schedules"]:
                    instructors = []
                    for instructor_data in schedule_data["instructors"]:
                        instructor = db.session.query(Instructor).filter_by(name=instructor_data["name"]).first()
                        if instructor is None:
                            instructor = Instructor(
                                name=instructor_data["name"],
                                instructor_type=instructor_data["type"]
                            )
                        instructors.append(instructor)
                    db.session.add_all(instructors)
                    schedule = Schedule(
                        location=schedule_data["building"] + " " + schedule_data["room"],
                        instructors=instructors,
                        days=schedule_data["days"],
                        time=schedule_data["time"],
                        term=term
                    )
                    schedules.append(schedule)
                db.session.add_all(schedules)

                db.session.add(Class(
                    course_id=course_id,
                    class_section=class_data["section"],
                    class_number=class_data["class_number"],
                    title=class_data["title"],
                    component=class_data["component"],
                    topics=class_data["topics"],
                    term=term,
                    hours=class_data["units"],
                    # meeting dates, instruction type not provided
                    schedules=schedules,
                    enrollment_cap=class_data["enrollment_cap"],
                    enrollment_total=class_data["enrollment_total"],
                    waitlist_cap=class_data["waitlist_cap"],
                    waitlist_total=class_data["waitlist_total"],
                    min_enrollment=class_data["min_enrollment"],
                    attributes=class_data["attributes"] if "attributes" in class_data else "",
                    combined_section_id=class_data[
                        "combined_section_id"] if "combined_section_id" in class_data else "",
                    equivalents=class_data["equivalents"] if "equivalents" in class_data else ""
                ))
            class_data = None
            continue
        # first line
        elif class_data is None:
            if line.startswith("Report"):
                class_data = {}
                continue
            line_data = [x for x in line.split(" ") if x.strip()]
            class_data = {}

            data_stage = ["dept", "catalog_number", "section", "class_number", "title", "component", "units", "topics"]
            altered_line = line.strip()
            while len(altered_line) > 0 and len(data_stage) > 0:
                if data_stage[0] == "title":
                    for component in ["Lecture", "Lab", "Recitation", "Independent Study", "Practicum",
                                      "Thesis Research", "Clinical", "Correspondence", "Field Work",
                                      "Inter_Institutional"]:
                        if component in altered_line:
                            class_data["title"] = altered_line[:altered_line.index(component)].strip()
                            data_stage.pop(0)
                            class_data["component"] = component
                            altered_line = altered_line[altered_line.index(component) + len(component):].strip()
                            break
                elif data_stage[0] == "units":
                    j = 0
                    while j < len(altered_line):
                        if not altered_line[j].isnumeric() and altered_line[j] not in [" ", "_"]:
                            break
                        j += 1
                    class_data["units"] = altered_line[:j].strip()
                    altered_line = altered_line[j:].strip()
                else:
                    if " " in altered_line:
                        class_data[data_stage[0]] = altered_line[:altered_line.index(" ")]
                        altered_line = altered_line[altered_line.index(" "):].strip()
                    else:
                        class_data[data_stage[0]] = altered_line
                        altered_line = ""
                data_stage.pop(0)
            continue
        elif line.startswith("Bldg:"):
            def find_nth(haystack, needle, n):
                start = haystack.find(needle)
                while start >= 0 and n > 1:
                    start = haystack.find(needle, start + len(needle))
                    n -= 1
                return start

            schedule = {"building": line[len("Bldg: "):line.index("Room: ")],
                        "room": line[line.index("Room:") + len("Room:"):line.index("Days:")].strip(),
                        "days": line[line.index("Days:") + len("Days:"):line.index("Time:")].strip(),
                        "time": line[line.index("Time:") + len("Time:"):
                                     find_nth(line[line.index("Time:") + len("Time:"):].strip(), ":", 2)
                                     + line.index("Time:")+len("Time: ")+4].strip()}
            if "schedules" not in class_data:
                class_data["schedules"] = []
            class_data["schedules"].append(schedule)
        elif "Instructor:" in line:
            if "schedules" not in class_data:
                print("Major error occurred!!!")
            if "instructors" not in class_data["schedules"][len(class_data["schedules"]) - 1]:
                class_data["schedules"][len(class_data["schedules"]) - 1]["instructors"] = []
            class_data["schedules"][len(class_data["schedules"]) - 1]["instructors"].append({
                "type": line[:line.index(" ")],
                "name": line[line.index("Instructor:") + len("Instructor:"):].strip()
            })
        elif line.startswith("Class Enrl Cap:"):
            class_data["enrollment_cap"] = line[len("Class Enrl Cap:"):line.index("Class Enrl Tot:")].strip()
            class_data["enrollment_total"] = line[line.index("Class Enrl Tot:") + len("Class Enrl Tot:"):line.index(
                "Class Wait Cap:")].strip()
            class_data["waitlist_cap"] = line[line.index("Class Wait Cap:") + len("Class Wait Cap:"):line.index(
                "Class Wait Tot:")].strip()
            class_data["waitlist_total"] = line[line.index("Class Wait Tot:") + len("Class Wait Tot:"):line.index(
                "Class Min Enrl:")].strip()
            class_data["min_enrollment"] = line[line.index("Class Min Enrl:") + len("Class Min Enrl:"):].strip()
        elif line.startswith("Attributes"):
            class_data["attributes"] = line[len("Attributes: "):]
        elif line.startswith("Combined Section ID"):
            class_data["combined_section_id"] = line[len("Combined Section ID:"):].strip()
        elif line.startswith("Class Equivalents"):
            class_data["equivalents"] = line[len("Class Equivalents:"):].strip()
    print(f"Created entries for {len(missing_courses)} missing courses: " + ",".join(missing_courses))


# gets data about courses from the catalog
def get_catalog_data():
    add_queue = []
    for subject in tqdm(subjects, position=0, leave=False, desc="Subjects"):
        response = requests.get(f"https://catalog.unc.edu/courses/{subject.lower()}/")

        soup = BeautifulSoup(str(response.content).replace("\\n", "")
                             .replace("\\xc2\\xa0", " ").encode('utf-8').decode("unicode_escape"), "html.parser")

        for course in tqdm(soup.select(".courseblock"), position=1, leave=False, desc=subject):
            course_block_title_parts = course.select_one(".courseblocktitle strong").contents[0].split(". ")
            attributes = []
            strong_text = ""
            other_text = ""
            description = ""
            has_hit_br = False
            for content_item in course.select_one(".courseblockdesc").contents:
                if content_item.name == "br":
                    if not has_hit_br:
                        description = other_text
                    has_hit_br = True
                    if strong_text != "" and other_text != "":
                        attributes.append(CourseAttribute(
                            label=strong_text.strip(),
                            value=other_text.strip().strip(".")))

                    strong_text = ""
                    other_text = ""
                elif content_item.name == "strong":
                    strong_text = content_item.contents[0].strip(":")
                else:
                    if isinstance(content_item, NavigableString):
                        other_text += content_item
                    else:
                        other_text += content_item.contents[0]
            add_queue.extend(attributes)
            add_queue.append(Course(
                code=course_block_title_parts[0].strip(),
                title=course_block_title_parts[1].strip(),
                credits=course_block_title_parts[2].strip(".").strip(),
                description=description.strip(),
                attrs=attributes,
                last_updated=datetime.datetime.utcnow()
            ))
    db.session.add_all(add_queue)


def update_unc_data():
    db.create_all()

    terms = ["2229"]
    text_terms = ["Fall 2022"]

    print(f"Deleted {db.session.query(Course).delete()} courses")
    print(f"Deleted {db.session.query(CourseAttribute).delete()} course attributes")
    get_catalog_data()
    db.session.commit()

    pdf_data(text_terms)
    db.session.commit()

    get_sections_data(terms)
    db.session.commit()


if __name__ == "__main__":
    update_unc_data()
