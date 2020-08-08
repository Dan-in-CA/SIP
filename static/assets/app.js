import $ from 'jquery';

window.$ = $;
window.jQuery = $;

import 'popper.js';
import 'bootstrap'
import 'eonasdan-bootstrap-datetimepicker'

window.dateString=function dateString(d) {
    let dateString = dayList [d.getDay()]; // Moved translatable text to base.html, dk
    dateString += " " + d.getDate() + " ";
    dateString += monthList [d.getMonth()]; // Moved translatable text to base.html, dk
    return dateString;
}

// require('./scripts/schedule');

import ClockHandler from './scripts/time';

window.addEventListener('DOMContentLoaded', (event) => {
    ClockHandler.init('#deviceTime')

});
