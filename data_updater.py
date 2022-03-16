import requests as requests
from tqdm import tqdm
from bs4 import BeautifulSoup, NavigableString

from models import Course, Class, db, Schedule


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


def update_unc_data():
    db.create_all()
    response = requests.get("https://reports.unc.edu/class-search/advanced_search/", params={
        "term": "2222",
        "advanced": "AERO, AAAD, AMST, ANTH,APPL, ARAB, ARCH, ARMY, ARTH, ASIA, ASTR, BIOC, BCB, BBSP, BIOL, BMME, BIOS, BCS, BUSI, CHIP, CBIO, CBPH, CBMC, CHEM, CHER, CHIN, PLAN, CLAR, CLAS, CLSC, CRMH, COMM, CMPL, COMP, EURO, CZCH, DENG, DHYG, DHED, DRAM, DTCH, ECON, EDUC, ENDO, ENGL, ENEC, ENVR, EPID, EXSS, EDMX, DPET, FOLK, FREN, GNET, GEOL, GEOG, GERM, GSLL, GLBL, GOVT, GRAD, GREK, HBEH, HPM, HEBR, HNUR, HIST, INLS, IDST, ITAL, JAPN, JWST, SWAH, KOR, LTAM, LATN, LFIT, LGLA, LING, MASC, MTSC, MHCH, MATH, MEJO, MCRO, MUSC, NAVS, NBIO, NSCI, NURS, NUTR, OCSC, OCCT, OPER, ORPA, ORAD, ORTH, PATH, PWAD, PEDO, PERI, PRSN, PHRS, DPMP, PHCO, PHCY, DPOP, PHIL, PHYA, PHYS, PHYI, PLSH, POLI, PORT, PACE, PROS, PSYC, PUBA, PUBH, PLCY, RADI, RECR, RELI, ROML, RUSS, SPHG, SLAV, SOWO, SOCI, SPAN, SPHS, STOR, ARTS, TOXC, TURK, WOLO, WGST, VIET"
    })

    print("got a response")
    soup = BeautifulSoup(str(response.content).replace("\\n", ""), "html.parser")

    rows = soup.select("#results-table > tbody > tr")
    static_class_data = {}
    for row in tqdm(rows):
        class_data = {}
        i = 0
        while i < len(row.contents):
            key = row.contents[i].split(";")[0].strip()
            value = get_root_text(row.contents[i+1])
            class_data[key] = value
            static_class_data[key] = value
            i += 2

        course_id = static_class_data["subject"] + " " + static_class_data["catalog number"]
        if db.session.query(Course.id).filter_by(id=course_id).first() is None:
            db.session.add(Course(
                id=course_id,
                subject=static_class_data["subject"],
                catalog_number=static_class_data["catalog number"],
                same_as_id=static_class_data["cross-listed courses"]
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

    print("committing data")
    db.session.commit()


if __name__ == "__main__":
    update_unc_data()

