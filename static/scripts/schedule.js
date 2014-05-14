function checkMatch(programs, simdate) {
	// simdate is Java date object, simday is the #days since 1970 01-01
	var run = [];
	for (var p in programs) {
		var prog = programs[p];
		var enabled = prog[0];
		var days = prog[1];
		var dayInterval = prog[2];
		var startTime = prog[3];
		var endTime = prog[4];
		var interval = prog[5];
		var duration = prog[6] * wl/100;
		if (enabled == 0 || duration == 0) {
			continue;
		}
		if ((days&0x80) && (dayInterval>1)) {	// inverval checking
			var simday = Math.floor(simdate/(24*60*60*1000));
			if ((simday % dayInterval) != (days&0x7f))  {
				continue; // remainder checking
			}
		} else {
			var weekday = (simdate.getDay()+6)%7; // getDay assumes sunday is 0, converts to Monday 0
			if ((days & (1<<weekday)) == 0) {
				continue; // weekday checking
			}
			var date = simdate.getDate(); // day of the month
			if ((days&0x80) && (dayInterval == 0)) { // even day checking
				if ((date%2) !=0)	{
					continue;
				}
			}
			if ((days&0x80) && (dayInterval == 1)) { // odd day checking
				if (date==31) {
					continue;
				} else if (date==29 && simdate.getUTCMonth()==1) {
					continue;
				} else if ((date%2)==1) {
					continue;
				}
			}
		}
		var timer = startTime;
		do {
			var programTimer = timer;
			for (bid=0; bid<nbrd; bid++) {
				for (s=0; s<8; s++) {
					var sid = bid*8 + s;
					if (mas == (sid+1)) continue; // skip master station
					if (prog[7+bid]&(1<<s)) {
						run.push({
							program: (parseInt(p) + 1).toString(),
							station: sid,
							start: programTimer,
							duration: duration
						});
						programTimer += duration/60;
					}
				}
			}
			timer += interval;
		} while (timer < endTime);
	}
	return run;
}

function toXSDate(d) {
	var r = d.getFullYear() + "-" +
			(d.getMonth() < 9 ? "0" : "") + (d.getMonth()+1) + "-" +
			(d.getDate() < 10 ? "0" : "") + d.getDate();
	return r;
}

function toClock(duration) {
	var h = Math.floor(duration/60);
	var m = Math.floor(duration - (h*60));
	return (h<10 ? "0" : "") + h + ":" + (m<10 ? "0" : "") + m;
}

function fromClock(clock) {
	var components = clock.split(":");
	var duration = 0;
	for (var c in components) {
		duration = duration*60 + parseInt(components[c], 10);
	}
	return duration;
}

function programName(p) {
	if (p == "Manual" || p == "Run-once") {
		return p + " Program";
	} else {
		return "Program " + p;
	}
}

var displayScheduleDate = new Date();
var displayScheduleTimeout;

function displaySchedule(schedule) {
	if (displayScheduleTimeout != null) {
		clearTimeout(displayScheduleTimeout);
	}
	var now = new Date();
	var nowMark = now.getHours()*60 + now.getMinutes();
	var isToday = toXSDate(displayScheduleDate) == toXSDate(now);
	var programClassesUsed = new Object();
	jQuery(".stationSchedule .scheduleTick").each(function() {
		jQuery(this).empty();
		var sid = jQuery(this).parent().attr("data");
		var slice = parseInt(jQuery(this).attr("data"))*60;
		var boxes = jQuery("<div class='scheduleMarkerContainer'></div>");
		for (var s in schedule) {
			if (schedule[s].station == sid) {
				if (!(isToday && schedule[s].date == undefined && schedule[s].start + schedule[s].duration/60 < nowMark)) {
					var relativeStart = schedule[s].start - slice;
					var relativeEnd = schedule[s].start + schedule[s].duration/60 - slice;
					if (0 <= relativeStart && relativeStart < 60 ||
						0.05 < relativeEnd && relativeEnd <= 60 ||
						relativeStart < 0 && relativeEnd >= 60) {
						var barStart = Math.max(0,relativeStart)/60;
						var barWidth = Math.max(0.05,Math.min(relativeEnd, 60)/60 - barStart);
						var programClass;
						if (schedule[s].program == "Manual" || schedule[s].program == "Run-once") {
							programClass = "programManual";
						} else {
							programClass = "program" + (parseInt(schedule[s].program)+1)%10;
						}
						programClassesUsed[schedule[s].program] = programClass;
						var markerClass = (schedule[s].date == undefined ? "schedule" : "history");
						boxes.append("<div class='scheduleMarker " + programClass + " " + markerClass + "' style='left:" + barStart*100 + "%;width:" + barWidth*100 + "%' title='" + programName(schedule[s].program) + ": " + toClock(schedule[s].start) + " for " + toClock(schedule[s].duration) + "'></div>");
					}
				}
			}
		}
		if (isToday && slice <= nowMark && nowMark < slice+60) {
			var stationOn = jQuery(this).parent().children(".stationStatus").hasClass("station_on");
			boxes.append("<div class='nowMarker" + (stationOn?" on":"")+ "' style='width:2px;left:"+ (nowMark-slice)/60*100 + "%;'>");
		}
		if (boxes.children().length > 0) {
			jQuery(this).append(boxes);
		}
	});
	jQuery("#legend").empty();
	for (var p in programClassesUsed) {
		jQuery("#legend").append("<span class='" + programClassesUsed[p] + "'>" + programName(p) + "</span>");
	}
	jQuery(".scheduleMarker").mouseover(scheduleMarkerMouseover);
	jQuery(".scheduleMarker").mouseout(scheduleMarkerMouseout);
	
	jQuery("#displayScheduleDate").text(dateString(displayScheduleDate) + (displayScheduleDate.getFullYear() == now.getFullYear() ? "" : ", " + displayScheduleDate.getFullYear()));
	if (isToday) {
		displayScheduleTimeout = setTimeout(displayProgram, 1*60*1000);  // every minute
	}
}

function displayProgram() {
	if (displayScheduleDate > new Date()) {
		var schedule = checkMatch(prog, displayScheduleDate);
		displaySchedule(schedule);
	} else {
		jQuery.getJSON("/api/log?date=" + toXSDate(displayScheduleDate), function(log) {
			for (var l in log) {
				log[l].duration = fromClock(log[l].duration);
				log[l].start = fromClock(log[l].start)/60;
			}
			if (toXSDate(displayScheduleDate) == toXSDate(new Date())) {
				var schedule = checkMatch(prog, displayScheduleDate);
				log = log.concat(schedule);
			}
			displaySchedule(log);
		})
	}
}


jQuery(document).ready(displayProgram);

function scheduleMarkerMouseover() {
	var description = jQuery(this).attr("title");
	var markerClass = jQuery(this).attr("class");
	markerClass = markerClass.substring(markerClass.indexOf("program"));
	markerClass = markerClass.substring(0,markerClass.indexOf(" "));
	jQuery(this).append('<span class="showDetails ' + markerClass + '">' + description + '</span>');
	jQuery(this).children(".showDetails").mouseover(function(){ return false; });
	jQuery(this).children(".showDetails").mouseout(function(){ return false; });
}
function scheduleMarkerMouseout() {
	jQuery(this).children(".showDetails").remove();
}


