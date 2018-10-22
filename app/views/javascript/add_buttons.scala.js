@import views.html.forms.inputText
@import views.html.forms.inputNumber
@import views.html.forms.checkBox
@import MachineController.FormID

@()
$( document ).ready(function() {
    var timeElements = 0;

    $( "#add-runtimer" ).click(function(e) {
        e.preventDefault();
        var template = $( ".template-runtimer" ).clone();
        template.removeClass('gone template-runtimer');
        $( 'label', template ).attr("for", "new_runtimer[0]");
        $( 'input', template ).attr("id", "new_runtimer[0]");
        $( 'input', template ).attr("name", "new_runtimer[0]");
        $( "#submit-button" ).before(template);
        $( "#add-runtimer" ).prop('disabled', true);
    });

    $( "#add-access-time" ).click(function(e) {
        e.preventDefault();
        var template = $( ".template-time" ).clone();
        template.removeClass('gone template-time');
        $( 'label:first', template ).attr("for", "new_weekdays[" + timeElements + "]");
        $( 'label > input', template ).attr("name", "new_weekdays[" + timeElements + "]");
        $( 'input#start_template', template ).attr("name", "new_start[" + timeElements + "]");
        $( 'input#start_template', template ).attr("id", "new_start[" + timeElements + "]");
        $( "label[for='start_template']", template ).attr("for", "new_start[" + timeElements + "]");
        $( 'input#end_template', template ).attr("name", "new_end[" + timeElements + "]");
        $( 'input#end_template', template ).attr("id", "new_end[" + timeElements + "]");
        $( "label[for='end_template']", template ).attr("id", "new_end[" + timeElements + "]");
        $( "#submit-button" ).before(template);
        timeElements++;
    });

    $('button#update_runtimer').click(function() {
        alert("Hello")
    });



});

