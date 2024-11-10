import * as bs from 'bootstrap'
import * as htmx from './htmx.min.js'
var jquery = require("jquery");
window.$ = window.jQuery = jquery; // notice the definition of global variables here
require("jquery-ui/dist/jquery-ui.js");

window.bootstrap = bs

window.urlMap = {

};

window.updateTooltips = function () {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bs.Tooltip(tooltipTriggerEl))

    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="token-popover"]')
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bs.Popover(popoverTriggerEl, {
        "html": true,
        "delay": 200,
        "content": function (e) {
            const token_pk = e.getAttribute('data-token-pk');
            $.ajax({
                url: window.urlMap['person-for-token-popover'] + '?token_pk=' + token_pk,
                success: function(response){
                    jquery('#'+token_pk).html(response);
                }
            });
            return '<div id="'+ token_pk +'">Loading...</div>';
        }
    }));
}

window.addEventListener('htmx:beforeRequest', function(event) {
    const alert = document.querySelector('.alert');
    if (alert) {
        alert.classList.add('invisible');
    }
});

window.addEventListener('htmx:beforeSwap', function(event) {
    if (event.detail.xhr.status >= 400) {
        event.detail.target.querySelector('.alert').classList.remove('invisible');
    }
});

window.addEventListener('htmx:afterSwap', function(event) {
    updateTooltips();
})