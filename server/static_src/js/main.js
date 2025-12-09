import * as bs from 'bootstrap'
import * as htmx from './htmx.min.js'
global.htmx = htmx;

import Chart from 'chart.js/auto';

window.Chart = Chart;

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

    const machinePopoverTriggerList = document.querySelectorAll('[data-bs-toggle="machine-popover"]')
    const machinePopovers = [...machinePopoverTriggerList].map(popoverTriggerEl =>
        new bs.Popover(popoverTriggerEl, {
        "html": true,
        "delay": 200,
        "content": function (e) {
            const machine_pk = e.getAttribute('data-machine-pk');
            $.ajax({
                url: window.urlMap['machine-popover'] + '?machine_pk=' + machine_pk,
                success: function(response){
                    jquery('#'+machine_pk).html(response);
                }
            });
            return '<div id="'+ machine_pk +'">Loading...</div>';
        }
    }));

    const personPopoverTriggerList = document.querySelectorAll('[data-bs-toggle="person-popover"]')
    console.log('Found person popovers:', personPopoverTriggerList.length);
    const personPopoverList = [...personPopoverTriggerList].map(popoverTriggerEl => new bs.Popover(popoverTriggerEl, {
        "html": true,
        "delay": 200,
        "content": function (e) {
            const person_pk = e.getAttribute('data-person-pk');
            $.ajax({
                url: window.urlMap['person-popover'] + '?person_pk=' + person_pk,
                success: function(response){
                    jquery('#'+person_pk).html(response);
                }
            });
            return '<div id="'+ person_pk +'">Loading...</div>';
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
        console.log('Error', event.detail.xhr.status);
        if (event.detail.target.querySelector('.alert')) {
            event.detail.target.querySelector('.alert').classList.remove('invisible');
        }
    }
});

window.addEventListener('htmx:afterSwap', function(event) {
    updateTooltips();
})