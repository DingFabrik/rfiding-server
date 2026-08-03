import * as htmx from './htmx.min.js'
import * as htmx_ws from './htmx-ws.js'
global.htmx = htmx;

import Chart from 'chart.js/auto';
import { createIcons, icons } from 'lucide';
import './keyboardshortcuts.js';

window.Chart = Chart;

var jquery = require("jquery");
window.$ = window.jQuery = jquery; // notice the definition of global variables here
require("jquery-ui/dist/jquery-ui.js");

window.urlMap = {

};

window.createIcons = function () {
    createIcons({ icons });
}

window.openModal = function (id) {
    const dialog = document.getElementById(id);
    dialog?.showModal();
    dialog?.querySelector('[autofocus]')?.focus();
}

window.closeModal = function (id) {
    document.getElementById(id)?.close();
}

document.addEventListener('click', function (event) {
    const opener = event.target.closest('[data-modal-target]');
    if (opener) {
        event.preventDefault();
        openModal(opener.getAttribute('data-modal-target'));
        return;
    }
    const closer = event.target.closest('[data-modal-close]');
    if (closer) {
        closer.closest('dialog')?.close();
    }
});

function initPopover(toggle, pkAttr, urlKey) {
    document.querySelectorAll('[data-popover-toggle="' + toggle + '"]').forEach((trigger) => {
        if (trigger.dataset.popoverInitialized) {
            return;
        }
        trigger.dataset.popoverInitialized = 'true';
        const pk = trigger.getAttribute(pkAttr);
        if (!pk) {
            return;
        }
        const content = document.createElement('div');
        content.setAttribute('popover', 'auto');
        content.className = 'dropdown card card-sm w-64 bg-base-100 shadow-lg p-4';
        content.id = pk;
        content.innerHTML = 'Loading...';
        document.body.appendChild(content);

        let hideTimeout = null;
        const cancelHide = () => {
            if (hideTimeout) {
                clearTimeout(hideTimeout);
                hideTimeout = null;
            }
        };
        const scheduleHide = () => {
            cancelHide();
            hideTimeout = setTimeout(() => content.hidePopover(), 200);
        };
        const show = () => {
            cancelHide();
            if (content.matches(':popover-open')) {
                return;
            }
            const rect = trigger.getBoundingClientRect();
            content.style.position = 'fixed';
            content.style.inset = 'auto';
            content.style.margin = '0';
            content.style.top = (rect.bottom + 4) + 'px';
            content.style.left = rect.left + 'px';
            content.showPopover();
            if (content.dataset.loaded) {
                return;
            }
            content.dataset.loaded = 'true';
            $.ajax({
                url: window.urlMap[urlKey] + '?' + pkAttr.replace(/^data-/, '').replace(/-/g, '_') + '=' + pk,
                success: function (response) {
                    $('#' + pk).html(response);
                }
            });
        };

        trigger.addEventListener('mouseenter', show);
        trigger.addEventListener('focus', show);
        trigger.addEventListener('mouseleave', scheduleHide);
        trigger.addEventListener('blur', scheduleHide);
        content.addEventListener('mouseenter', cancelHide);
        content.addEventListener('mouseleave', scheduleHide);
    });
}

window.initPopovers = function () {
    initPopover('token-popover', 'data-token-pk', 'person-for-token-popover');
    initPopover('machine-popover', 'data-machine-pk', 'machine-popover');
    initPopover('person-popover', 'data-person-pk', 'person-popover');
}

document.addEventListener('click', function (event) {
    const tab = event.target.closest('[data-tabs-target]');
    if (!tab) {
        return;
    }
    const tabList = tab.closest('[role="tablist"]');
    const paneId = tab.getAttribute('data-tabs-target');
    const pane = document.querySelector(paneId);
    if (!tabList || !pane) {
        return;
    }
    tabList.querySelectorAll('[data-tabs-target]').forEach((btn) => {
        btn.classList.remove('tab-active');
        btn.setAttribute('aria-selected', 'false');
    });
    tabList.parentElement.querySelectorAll('[role="tabpanel"]').forEach((p) => {
        p.classList.add('hidden');
    });
    tab.classList.add('tab-active');
    tab.setAttribute('aria-selected', 'true');
    pane.classList.remove('hidden');
});

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
    initPopovers();
    createIcons();
})

window.addEventListener('htmx:responseError', function(event) {
    event.detail.target.innerHTML = '<div class="alert alert-error" role="alert"><h4 class="font-bold">An error occurred.</h4><span>' + event.detail.xhr.statusText + '</span></div>';
});
