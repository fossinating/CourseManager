def generate_color(class_code):
    dept_value = sum([ord(character) for character in class_code.split()[0]])
    code_value = sum([ord(character) for character in class_code.split()[1]])

    return f"{(dept_value % 180) + (code_value / 600.0 * 360*20 % 180)},70%,80%,1"


def human_time(mil_time):
    if "TBA" in mil_time:
        return mil_time
    times = mil_time.split(" - ")
    human_times = []
    for time in times:
        hour = int(time[:2])
        minute = int(time[3:])
        if hour > 11:
            human_times.append(f"{(hour-1)%12+1}:{minute:02d}pm")
        else:
            human_times.append(f"{hour}:{minute:02d}am")
    return " - ".join(human_times)


def humanize_hour(hour):
    return f"{(hour-1)%12+1}{'pm' if hour >= 12 else 'am'}"

# def format_description(description):


