import requests as requests
from tqdm import tqdm
from bs4 import BeautifulSoup, NavigableString
from urllib3.exceptions import NewConnectionError, MaxRetryError
from tika import parser

from models import Course, Class, db, Schedule, Instructor


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


subjects = ("AERO", "AAAD", "AMST", "ANTH", "APPL", "ARAB", "ARCH", "ARMY", "ARTH", "ASIA", "ASTR", "BIOC", "BCB", "BBSP", "BIOL", "BMME", "BIOS", "BCS", "BUSI", "CHIP", "CBIO", "CBPH", "CBMC", "CHEM", "CHER", "CHIN", "PLAN", "CLAR", "CLAS", "CLSC", "CRMH", "COMM", "CMPL", "COMP", "EURO", "CZCH", "DENG", "DHYG", "DHED", "DRAM", "DTCH", "ECON", "EDUC", "ENDO", "ENGL", "ENEC", "ENVR", "EPID", "EXSS", "EDMX", "DPET", "FOLK", "FREN", "GNET", "GEOL", "GEOG", "GERM", "GSLL", "GLBL", "GOVT", "GRAD", "GREK", "HBEH", "HPM", "HEBR", "HNUR", "HIST", "INLS", "IDST", "ITAL", "JAPN", "JWST", "SWAH", "KOR", "LTAM", "LATN", "LFIT", "LGLA", "LING", "MASC", "MTSC", "MHCH", "MATH", "MEJO", "MCRO", "MUSC", "NAVS", "NBIO", "NSCI", "NURS", "NUTR", "OCSC", "OCCT", "OPER", "ORPA", "ORAD", "ORTH", "PATH", "PWAD", "PEDO", "PERI", "PRSN", "PHRS", "DPMP", "PHCO", "PHCY", "DPOP", "PHIL", "PHYA", "PHYS", "PHYI", "PLSH", "POLI", "PORT", "PACE", "PROS", "PSYC", "PUBA", "PUBH", "PLCY", "RADI", "RECR", "RELI", "ROML", "RUSS", "SPHG", "SLAV", "SOWO", "SOCI", "SPAN", "SPHS", "STOR", "ARTS", "TOXC", "TURK", "WOLO", "WGST", "VIET")


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
            if db.session.query(Course.catalog_number).filter_by(catalog_number=course["key"], srcdb=course["srcdb"]).first() is None:
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


def get_sections_data():
    response = requests.get("https://reports.unc.edu/class-search/advanced_search/", params={
        "term": "2222",
        "advanced": ", ".join(subjects)
    })

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
            print(f"The course {course_id} does not already exist!")
            db.session.add(Course(
                code=course_id,
                title=class_data["course description"],
                hours=class_data["credit hours"]
            ))

        class_number = safe_cast(class_data["class number"], int, -1)

        db.session.add(Schedule(
            schedule=class_data["schedule"],
            class_id=class_number
        ))

        if db.session.query(Class.class_number).filter_by(class_number=class_number).first() is None:
            db.session.add(Class(
                course_id=course_id,
                class_section=class_data["section number"],
                class_number=class_number,
                title=class_data["course description"],
                term=class_data["term"],
                hours=safe_cast(class_data["credit hours"], float, -1.0),
                meeting_dates=class_data["meeting dates"],
                room=class_data["room"],
                instruction_type=class_data["instruction mode"],
                available_seats=safe_cast(class_data["available seats"], int, -1)
            ))


def pdf_data():
    raw = parser.from_file("ssb.pdf")
    class_data = {}
    for line in tqdm(raw["content"].strip().split("\n"), position=0):
        if line.strip() == "":
            continue
        if "_____" in line:
            if len(class_data) > 0:
                course_id = class_data["dept"] + " " + class_data["catalog_number"]
                # check to see if the course exists, if not leave a warning
                if db.session.query(Course.code).filter_by(code=course_id).first() is None:
                    print(f"The course {course_id} does not already exist!")
                    db.session.add(Course(
                        code=course_id,
                        title=class_data["title"],
                        hours=class_data["units"]
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
                            db.session.add(instructor)
                        instructors.append(instructor)
                    schedule = Schedule(
                        location=schedule_data["building"] + " " + schedule_data["room"],
                        instructors=instructors,
                        days=schedule_data["days"],
                        time=schedule_data["time"]
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
                    hours=class_data["units"],
                    term="FALL 2022",
                    schedules=schedules,
                    enrollment_cap=class_data["enrollment_cap"],
                    enrollment_total=class_data["enrollment_total"],
                    waitlist_cap=class_data["waitlist_cap"],
                    waitlist_total=class_data["waitlist_total"],
                    min_enrollment=class_data["min_enrollment"],
                    attributes=class_data["attributes"] if "attributes" in class_data else "",
                    combined_section_id=class_data["combined_section_id"] if "combined_section_id" in class_data else "",
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

            i = 0
            combined_data = []
            data_stage = ["dept", "catalog_number", "section", "class_number", "title", "component", "units", "topics"]
            altered_line = line
            while i < len(line_data) and len(data_stage) > 0:
                if data_stage[0] != "title" and data_stage[0] != "topics":
                    class_data[data_stage[0]] = line_data[i]
                    data_stage.pop(0)
                else:
                    if data_stage[0] == "title":
                        for component in ["Lecture", "Lab", "Recitation", "Independent Study", "Practicum",
                                        "Thesis Research", "Clinical", "Correspondence", "Field Work",
                                          "Inter_Institutional"]:
                            if component in line_data[i]:
                                combined_data.append(line_data[i][:line_data[i].index(component)])
                                combined_data.clear()
                                class_data[data_stage[0]] = " ".join(combined_data)
                                data_stage.pop(0)
                                class_data[data_stage[0]] = component
                                data_stage.pop(0)
                                break
                    if line_data[i] == "A" and data_stage[0] == "topics":
                        i -= 1
                        class_data[data_stage[0]] = " ".join(combined_data)
                        combined_data.clear()
                        data_stage.pop(0)
                    combined_data.append(line_data[i])
                i += 1
            continue
        elif line.startswith("Bldg:"):
            schedule = {"building": line[len("Bldg: "):line.index("Room: ")],
                        "room": line[line.index("Room:") + len("Room:"):line.index("Days:")].strip(),
                        "days": line[line.index("Days:") + len("Days:"):line.index("Time:")].strip(),
                        "time": line[line.index("Time:") + len("Time:"):].strip()}
            if "schedules" not in class_data:
                class_data["schedules"] = []
            class_data["schedules"].append(schedule)
        elif "Instructor:" in line:
            if "schedules" not in class_data:
                print("Major error occurred!!!")
            if "instructors" not in class_data["schedules"][len(class_data["schedules"])-1]:
                class_data["schedules"][len(class_data["schedules"])-1]["instructors"] = []
            class_data["schedules"][len(class_data["schedules"])-1]["instructors"].append({
                "type": line[:line.index(" ")],
                "name": line[line.index("Instructor:") + len("Instructor:"):].strip()
            })
        elif line.startswith("Class Enrl Cap:"):
            class_data["enrollment_cap"] = line[len("Class Enrl Cap:"):line.index("Class Enrl Tot:")].strip()
            class_data["enrollment_total"] = line[line.index("Class Enrl Tot:") + len("Class Enrl Tot:"):line.index("Class Wait Cap:")].strip()
            class_data["waitlist_cap"] = line[line.index("Class Wait Cap:") + len("Class Wait Cap:"):line.index("Class Wait Tot:")].strip()
            class_data["waitlist_total"] = line[line.index("Class Wait Tot:") + len("Class Wait Tot:"):line.index("Class Min Enrl:")].strip()
            class_data["min_enrollment"] = line[line.index("Class Min Enrl:") + len("Class Min Enrl:"):].strip()
        elif line.startswith("Attributes"):
            class_data["attributes"] = line[len("Attributes: "):]
        elif line.startswith("Combined Section ID"):
            class_data["combined_section_id"] = line[len("Combined Section ID:"):].strip()
        elif line.startswith("Class Equivalents"):
            class_data["equivalents"] = line[len("Class Equivalents:"):].strip()


def update_unc_data():
    db.create_all()

    #get_unc_course_data()
    #db.session.commit()

    #get_sections_data()

    pdf_data()

    print("committing data")
    db.session.commit()


if __name__ == "__main__":
    update_unc_data()

