let _cliTzOffset = 0;
let _devTzOffset = 0;
let _timeFormat;
let $_wrapper;

const getDateString = (d) => {
    let dateString = dayList [d.getDay()]; // Moved translatable text to base.html, dk
    dateString += " " + d.getDate() + " ";
    dateString += monthList [d.getMonth()]; // Moved translatable text to base.html, dk
    return dateString;
}

const getTime = () => {
    return new Date(Date.now() + cliTzOffset - devTzOffset);
}

const appendToHtml = (date, hour, minute, second, ampm) => {
    let classMap = {
        'date': date,
        'hour': addPaddingZero(hour),
        'minute': addPaddingZero(minute),
        'second': addPaddingZero(second),
        'ampm': ampm,
    }

    for (const property in classMap) {
        let elem = $_wrapper.querySelector('.' + property);
        let val = classMap[property]
        if (elem && val) {
            elem.innerHTML = val;
        }
    }

}

const addPaddingZero = (number) => {
    return number < 10 ? '0' + number : number;
}

const updateClock = () => {

    let now = getTime();
    if (timeFormat) {
        appendToHtml(getDateString(now), now.getHours(), now.getMinutes(), now.getSeconds());
    } else {
        let hours = (now.getHours() % 12 === 0 ? "12" : now.getHours() % 12)
        let ampm = (now.getHours() >= 12 ? "pm" : "am");
        appendToHtml(getDateString(now), hours, now.getMinutes(), now.getSeconds(), ampm);

    }

}


const init = (selector, cliTzOffset, devTzOffset, timeFormat = null) => {
    _cliTzOffset = cliTzOffset;
    _devTzOffset = devTzOffset;
    _timeFormat = timeFormat;

    $_wrapper = document.querySelector(selector);
    if (!$_wrapper) {
        console.error(`selector ${selector} doesn't exist`)
        return;
    }

    updateClock()
    $_wrapper.classList.add('show')
    setInterval(updateClock, 1000);

}


module.exports = {init};
