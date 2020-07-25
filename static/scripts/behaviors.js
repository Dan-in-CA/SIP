// Set up a live clock based on device time

function dateString(d) {
	var dateString = dayList [d.getDay()]; // Moved translatable text to base.html, dk
	dateString += " " + d.getDate() + " ";
	dateString += monthList [d.getMonth()]; // Moved translatable text to base.html, dk
	return dateString;
}

function updateClock() { // Controls time and date clock.
	// Do our best to match this clock with the device clock (instead of the client device clock)
	var now = new Date(Date.now() + cliTzOffset - devTzOffset);

	/*
		Uncomment to test styling - sets a random time
		now.setHours(Math.floor(Math.random()*24));
		now.setMinutes(Math.floor(Math.random()*60));
	*/

	if (timeFormat) {
		jQuery("#deviceTime span.time").html((now.getHours() < 10 ? "0" : "") + now.getHours() + "<span class='sep'>:</span>" + (now.getMinutes() < 10 ? "0" : "") + now.getMinutes());
		jQuery("#deviceTime span.ampm").html("");
	} else {
		jQuery("#deviceTime span.time").html((now.getHours()%12 == 0 ? "12" : now.getHours() % 12) + "<span class='sep'>:</span>" + (now.getMinutes() < 10 ? "0" : "") + now.getMinutes());
		jQuery("#deviceTime span.ampm").html((now.getHours() >= 12 ? "pm" : "am"));
	}
	jQuery("#deviceTime span.second").text(":" + (now.getSeconds() < 10 ? "0" : "") + now.getSeconds());

	jQuery("#deviceDate").text(dateString(now));
}

// Initialize standard behaviors
jQuery(document).ready(function(){



	jQuery("button#bHome").click(function(){
		window.location = "/";
	});
	jQuery("button#bOptions").click(function(){
		window.location = "/vo";
	});
	jQuery("button#bStations").click(function(){
		window.location = "/vs";
	});
	jQuery("button#bPrograms").click(function(){
		window.location = "/vp";
	});
	jQuery("button#bRunOnce").click(function(){
		window.location = "/vr";
	});
	jQuery("button#bLog").click(function(){
		window.location = "/vl";
	});
	jQuery("button#bLogout").click(function(){
		window.location = "/logout";
	});

    jQuery("button#bHelp").click(function(){
		window.open("https://github.com/Dan-in-CA/SIP/wiki", "_blank");
	});

	// start the clock now, and update every second
	updateClock();
	setInterval(updateClock, 1000);

});
