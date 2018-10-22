// Register checkBox function as click handler
$('.click-handler input[type=checkbox]').click(checkBox);

// Toggle token activated state
function checkBox() {
    // retrieve CSRF token
    var token = $('input[name="csrfToken"]').attr('value')
    // put CSRF token in ajax header
    $.ajaxSetup({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('Csrf-Token', token);
        }
    });

    var box = $(this);
    var ok  = box.siblings("#ok");
    var nok = box.siblings("#nok");

    // prepare data to send
    var dataToSend = JSON.stringify({ id: box.val()});

    $.ajax( {
        type: 'POST',
        url: '/tokens/check',
        data: dataToSend,
        dataType: 'text',
        contentType: 'application/json',
        success: function(data) {
            ok.css("display", "inline");
            setTimeout(function () {
                ok.css("display", "none");
            }, 1000);
        },
        error: function(data) {
            console.log("Error: " + data);
            nok.css("display", "inline");
            setTimeout(function () {
                nok.css("display", "none");
            }, 1500);
        }
    } );
}


