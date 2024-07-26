//  Recommended first step - search and replace "proto_" with your own plugin name

/*
    Use this mechanism for changes that get triggered once when the page is loaded.

    Rename this function and references to it so it doesn't conflict with functions defined by any other plugins
*/
function proto_update_onload() {
    /* your custom UI change code here */
    // You can scope these changes to a specific page, look up in urls.py (e.g. home=="/", programs="/vp", runonce ="/vr" etc.)
    if (window.location.pathname == "/") {
        console.log("plugin home page ui one-time update");
    }

    /* end custom UI code */
}

// Update this with your specific function name
jQuery(document).ready(proto_update_onload);


/*
    Use this mechanism for changes that get triggered on a regular schedule (e.g. once a minute).

    Rename this function and references to it so it doesn't conflict with functions defined by any other plugins
*/
function proto_update_periodically() {
    /* your custom UI change code here */
    // You can scope these changes to a specific page, look up in urls.py (e.g. home=="/", programs="/vp", runonce ="/vr" etc.)
    if (window.location.pathname == "/") {
        console.log("plugin home page ui periodic update");
    }
    /* end custom UI code */
}

jQuery(document).ready(function(){
    // Update with your specific function name
    proto_update_periodically();  // Call once now
    // Update with your specific function name and the requested update interval
    setInterval(proto_update_periodically, 1000*60);  // Can call again every <n> milliseconds
});



/*
    Use this mechanism for changes that must be refreshed every time the data within the page changes.
    Notably, the schedule view updates periodically (once a minute) as well as when the use interacts by navigating 
    to a separate day.  Thus a UI change that needs to correlate with the currently displayed schedule can use this
    mechanism to insert updates every time the schedule does.

    Rename this function and references to it so it doesn't conflict with functions defined by any other 
    
*/
function proto_update_schedule() {
    /* your custom UI change code here */
    console.log("plugin home page schedule-change update")
    // The following illustrates calling the plugin via API to obtain current data in json format.
    // Illustrates passing a parameter, in this case representing the date used by the schedule display
    $.get( "/proto-data", {"date" : toXSDate(displayScheduleDate)}, function( data ) {
        // data is json passed back from the plugin, add code here to manipulate the UI accordingly
        console.log("plugin data from API: ");
        console.log(data);
    });
    /* end custom UI code */
}

jQuery(document).ready(function(){
    // An observer will monitor an element of the UI and trigger every time it changes.
    // In this case, every time the schedule view for the home page is updated we know that "displayScheduleDate" changes, 
    // and we can piggyback on that to make our own UI changes
    
    // Scope these changes to a specific page, look up in urls.py (e.g. home=="/", programs="/vp", runonce ="/vr" etc.)
    if (window.location.pathname == "/") {
        // Update with your specific function name
        if ($('#displayScheduleDate').length > 0) {
            // Verify the schedule is available (i.e. not in Manual mode)
            observer = new MutationObserver(proto_update_schedule);
            observer.observe($('#displayScheduleDate')[0], {characterData: true, childList:true, subTree: true});
        }
    }
});