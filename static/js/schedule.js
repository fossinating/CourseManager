schedule = get_active_schedule()


$.ajax({
    url: "/api/schedule",
    method: "POST",
    data: JSON.stringify(schedule),
    contentType: "application/json",
    dataType: "json",
    success: function(data) {
        for (let i = 0; i < data.length; i++){
            $(data[i]["parent"]).append(data[i]["html"])
        }
    },
    error: function(data) {
        $("#schedule-container").html("<h2>Failed to load schedule, please try again later</h2>");
        console.log(data)
    }
})

let styles = ""
for (let i = 0; i < schedule["classNumbers"].length; i++) {
    const class_number = schedule['classNumbers'][i]
    const color = "hsla(" + (Math.round(class_number*3 % 360)).toString() + ",70%,80%,1)";
    styles += "\n.class_slot[class_number=\"" + class_number + "\"] {\nbackground-color: " + color + ";\n}"
}
$("<style>" + styles + "</style>").appendTo("head")


function class_details(class_number) {
    $(".class-description.visible").removeClass("visible");
    $("#class-descriptions").addClass("visible");
    $(".class-description[class_number='" + class_number + "']").addClass("visible");
}

function close_class_details(){
    $("#class-descriptions").removeClass("visible")
}

function remove_class(class_number) {
    let schedule = get_active_schedule()
    const index = schedule["classNumbers"].indexOf(class_number)
    if (index > -1){
        schedule["classNumbers"].splice(index, 1)
    }
    save_schedule(schedule)
    $(".class_slot[class_number='" + class_number +"']").remove()
    close_class_details()
}