elements = document.getElementsByClassName("onUpdate");
for (var i = 0; i < elements.length; i++) {
    elements[i].addEventListener("input", update_search);
}

function update_search(){
    $("#search-form").submit();
}

var request_id = 0
var loaded_id = 0

function add_class(class_number){
    let schedule = get_active_schedule()
    if (!schedule.classNumbers.includes(class_number)){
        schedule.classNumbers.push(class_number)
        save_schedule(schedule)
    }

    $(".class-result[class_id='" + class_number + "']").addClass("inSchedule")
}


function updateClasses() {
    var schedule = get_active_schedule()
    $(".class-result").each(function(index){
        if (schedule.classNumbers.includes($(this).attr("class_id"))){
            $(this).addClass("inSchedule")
        } else {
            $(this).removeClass("inSchedule")
        }
    })
}


function toggleMode(){
    $("#results-container").toggleClass("tiled")
    $("#results-container").toggleClass("rows")
}


// this is the id of the form
$("#search-form").submit(function(e) {

    e.preventDefault(); // avoid to execute the actual submit of the form.

    var form = $(this);
    var actionUrl = form.attr('action');
    request_id += 1
    var _request = request_id
    $.ajax({
        type: "POST",
        url: actionUrl,
        data: form.serialize(), // serializes the form's elements.
        success: function(data)
        {
            if (loaded_id < _request) {
                loaded_id = _request;
                $("#results-container").html(data);
                updateClasses();
            }
        }
    });
});