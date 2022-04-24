function get_active_schedule(){
    let active_schedule_id = window.localStorage.getItem("active_schedule");
    const schedules = get_schedules();
    if (!active_schedule_id) {
        active_schedule_id = Object.keys(schedules)[0]
        set_active_schedule(active_schedule_id)
    }
    return schedules[active_schedule_id]
}


function get_schedules(){
    let schedules = window.localStorage.getItem("schedules");
    if (!schedules){
        const schedule = create_new_schedule();
        schedules = {
            [schedule.id] : schedule
        }
        save_schedules(schedules)
    } else {
        schedules = JSON.parse(schedules)
    }

    return schedules
}


// saves only one schedule, not modifying the others
function save_schedule(schedule){
    let schedules = get_schedules()
    schedules[schedule.id] = schedule
    save_schedules(schedules)
}

function save_schedules(schedules){
    window.localStorage.setItem("schedules", JSON.stringify(schedules));
}


function set_active_schedule(active_schedule){
    window.localStorage.setItem("active_schedule", active_schedule)
}


function create_new_schedule(){
    const id = window.crypto.randomUUID();
    return {
        "id": id,
        "displayName": "New Schedule",
        "classNumbers": []
    }
}