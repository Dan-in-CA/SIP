// Set up a live clock based on device time

//var deviceTimeOffset = devt - (tz/4-12)*3600000 - Date.now();

function dateString(d) {
	var dateString = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][d.getDay()];
	dateString += " " + d.getDate() + " ";
	dateString += ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][d.getMonth()];
	return dateString;
}

function updateClock() {
	var now = new Date(Date.now()); // + deviceTimeOffset);
	if (timeFormat) {
		jQuery("#deviceTime span.hour").text((now.getHours() < 10 ? "0" : "") + now.getHours());
		jQuery("#deviceTime span.ampm").text("");
	} else {
		jQuery("#deviceTime span.hour").text(now.getHours()%12 == 0 ? "12" : now.getHours() % 12);
		jQuery("#deviceTime span.ampm").text((now.getHours() > 12 ? "pm" : "am"));
	}
	jQuery("#deviceTime span.minute").text((now.getMinutes() < 10 ? "0" : "") + now.getMinutes());
	jQuery("#deviceTime span.second").text(":" + (now.getSeconds() < 10 ? "0" : "") + now.getSeconds());
	
	jQuery("#deviceDate").text(dateString(now));
	
	setTimeout(updateClock, 500);
}
		
// Initialize behaviors
jQuery(document).ready(function(){
	jQuery("#heat")
		.mouseenter(function() {
			jQuery(this).toggleClass("bluebg",true);
		})
		.mouseleave(function() {
			jQuery(this).toggleClass("bluebg",false);
		})
		.click(function() {
			jQuery("input[name='tunit']").val(tempunit);
			jQuery("form[name='tt']").submit();
		});
	var temp = parseFloat(cputemp);
	if (isNaN(temp)) {
		jQuery("#heat").html("n/a");
	} else {
		jQuery("#heat").html((tempunit == "F" ? Math.round(10*(9/5*cputemp+32))/10 : cputemp) + "&deg;" + tempunit);		
	}
	
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

	// start the clock
	updateClock();
});
