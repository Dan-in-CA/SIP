import $ from 'jquery';
import 'popper.js';
import 'bootstrap'
// import 'eonasdan-bootstrap-datetimepicker'

import ClockHandler from './scripts/time';

window.$ = $;
window.jQuery = $;

window.dateString = function dateString(d) {
    let dateString = dayList [d.getDay()]; // Moved translatable text to base.html, dk
    dateString += " " + d.getDate() + " ";
    dateString += monthList [d.getMonth()]; // Moved translatable text to base.html, dk
    return dateString;
}

window.addEventListener('DOMContentLoaded', (event) => {
    ClockHandler.init('#deviceTime')
  window.schedule= require( './scripts/schedule');
});
