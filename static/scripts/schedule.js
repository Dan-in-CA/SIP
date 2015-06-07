// Global vars
var displayScheduleDate = new Date(Date.now() + cliTzOffset - devTzOffset); // dk
var displayScheduleTimeout;
var sid,sn,t;
var simdate = displayScheduleDate; // date for simulation
if (typeof progs !== 'undefined'){var nprogs = progs.length}; // number of programs
if (typeof nbrd !== 'undefined'){var nst = nbrd*8}; // number of stations

function scheduledThisDate(pd,simminutes,simdate) { // check if progrm is scheduled for this date (displayScheduleDate) called from doSimulation
  // simminutes is minute count generated in doSimulation()
  // simdate is a JavaScript date object
  simday = Math.floor(simdate/(1000*3600*24)) // The number of days since epoc
  var wd,dn,drem; // week day, Interval days, days remaining
  if(pd[0]==0)  return 0; // program not enabled, do not match
  if ((pd[1]&0x80)&&(pd[2]>1)) {  // if interval program...  
    if(((simday)%pd[2])!=(pd[1]&0x7f)) return 0; // remainder checking ##############	
  } else {
    wd=(simdate.getDay()+6)%7; // getDay assumes sunday is 0, converts to Monday to 0 (weekday index)
    if((pd[1]&(1<<wd))==0)  return 0; // weekday checking
    dt=simdate.getDate(); // set dt = day of the month
    if((pd[1]&0x80)&&(pd[2]==0)) { // even day checking...
	    if(dt%2) return 0; // if odd day (dt%2 == 1), no not match
	 }
    if((pd[1]&0x80)&&(pd[2]==1))  { // odd day checking...
      if(dt==31) return 0; // if 31st of month, do not match
      else if (dt==29 && simdate.getMonth()==1) return 0; // if leap year day, do not match
      else if (!(dt%2)) return 0; // if even day, do not match
    }
  }
  if(simminutes<pd[3] || simminutes>=pd[4])  return 0; // if simulated time is before start time or after stop time, do not match
  if(pd[5]==0)  return 0; // repeat time missing, do not match
  if(((simminutes-pd[3])/pd[5]>>0)*pd[5] == (simminutes-pd[3])) { // if programmed to run now...
    return 1; // scheduled for displayScheduleDate
  }
  return 0;  // no match found
}

function doSimulation() { // Create schedule by a full program simulation, was draw_program()
  //if(typeof(simstart)==='undefined') simstart = 0; // set parameter default
//  var simminutes=simstart; // start at time set by calling function or 0 as default
  var simminutes=0;
  var busy=0,match_found=0,endmin=0,bid,s,sid,pid;
  var st_array=new Array(nst); //start time per station in seconds (minutes since midnight)?
  var pid_array=new Array(nst); // program index per station
  var et_array=new Array(nst); // end time per station (duration in seconds adjusted by water level - and station delay??)
  var schedule=[]; // shedule will hold data to display
  for(sid=0;sid<nst;sid++)  { // for for each station...
    st_array[sid]=0;pid_array[sid]=0;et_array[sid]=0; // initilize element[station index]=0 for start time, program, end time 
  }
  do { // check through every program
    busy=0;
	 endmin=0;
    match_found=0;
    for(pid=0;pid<nprogs;pid++) { //for each program
      var pd=progs[pid]; //prog=program array, pd=program element at this index (program data)
      if(scheduledThisDate(pd,simminutes,simdate)) { //call scheduledThisDate function, if scheduled...
        for(sid=0;sid<nst;sid++) { //for each station...
          bid=sid>>3;s=sid%8; //set board index (bid) and station number per board (s) from station index (sid) 
          if(mas==(sid+1)) continue; // skip master station
          if(pd[7+bid]&(1<<s)) { // if this station is selected in this program...
				et_array[sid]=pd[6]*wl/100*wlx/100; // Set end time for this station to duration adjusted by water level
				pid_array[sid]=pid+1; // Set station element in pid array to program number (pid+1)
            match_found=1;
          }
        }
      }
    }	
    if(match_found) { // when a match is found...
      var acctime=simminutes*60; // accumulate time (acctime) set to simminutes converted to seconds
      if(seq) { // if operation is sequential...
        for(sid=0;sid<nst;sid++) { // for each station...
          if(et_array[sid]) { // if an end time is set...
            st_array[sid]=acctime; // set start time for this station to accumulated time 
			  acctime+=et_array[sid]; //increment accumulated time by end time (adjusted duration) for this station
            et_array[sid]=acctime; // set end time for this station to updated accumulated time
			  endmin = Math.ceil(et_array[sid]/60); // update end time
			  acctime+=sdt; // increment accumulated time by station delay time
            busy=1; // set system busy flag - prevents new scheduleing until current schedule is finished
          }//if
        }//for
      } else { // if operation is concurrent...
        for(sid=0;sid<nst;sid++) { // for each station...
          if(et_array[sid]) { // if an end time is set...
            st_array[sid]=simminutes*60; // set start time for this station to simminutes converted to seconds
            et_array[sid]=simminutes*60+et_array[sid]; // set end time for this station to end time shifted by start time
			  if ((et_array[sid]/60)>endmin) {endmin = Math.ceil((et_array[sid]/60))} // update endmin to whole minute
            busy=1; // set system busy flag - prevents new scheduleing until current schedule is complete
          }//if(et_array)
        }//for(sid)
      }//else(seq)
    }//if(match_found)
	// add to schedule
	for(sid=0;sid<nst;sid++) { // for each station
	  if(pid_array[sid]) { // if this station is included...
	    schedule.push({ // data for creating home page program display
			program: pid_array[sid], // program number
			station: sid, // station index
			start: st_array[sid]/60, // start time, minutes since midnight
			duration: et_array[sid]-st_array[sid], // duration in seconds
			label: toClock(st_array[sid]/60, timeFormat) + " for " + toClock(((et_array[sid]/60)-(st_array[sid]/60)), 1) // ***not the same as log data date element
		});
	  }
    }	  
    if (busy) { // if system buisy...
      if(seq&&simminutes!=endmin) simminutes=endmin; // move to end of system busy state.
      else simminutes++; // increment simulation time
      for(sid=0;sid<nst;sid++)  {st_array[sid]=0;pid_array[sid]=0;et_array[sid]=0;} // set all elements of arrays to zero
      busy=0;
    } else { // if system not buisy...
      simminutes++; // increment simulation time
    }
  } while(simminutes<=24*60); // simulation ends at 24 hours
  return schedule
}

function toXSDate(d) {
	var r = d.getFullYear() + "-" +
			(d.getMonth() < 9 ? "0" : "") + (d.getMonth()+1) + "-" +
			(d.getDate() < 10 ? "0" : "") + d.getDate();
	return r;
}

function toClock(duration, tf) {
	var h = Math.floor(duration/60);
	var m = Math.floor(duration - (h*60));
	if (tf == 0) {
		return (h>12 ? h-12 : h) + ":" + (m<10 ? "0" : "") + m + (h<12 ? "am" : "pm");
	} else {
		return (h<10 ? "0" : "") + h + ":" + (m<10 ? "0" : "") + m;
	}
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

// show timeline on home page
function displaySchedule(schedule) {
	if (displayScheduleTimeout != null) {
		clearTimeout(displayScheduleTimeout);
	}
	var now = new Date(Date.now() + cliTzOffset - devTzOffset); // will show device time
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
						boxes.append("<div class='scheduleMarker " + programClass + " " + markerClass + "' style='left:" + barStart*100 + "%;width:" + barWidth*100 + "%' data='" + programName(schedule[s].program) + ": " + schedule[s].label + "'></div>");
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

function displayProgram() { // Controls home page irrigation timeline
	//if (displayScheduleDate > devt) { //dk
	if (displayScheduleDate > new Date(Date.now() + cliTzOffset - devTzOffset)) { //dk
		var schedule = doSimulation(); //dk
		displaySchedule(schedule);
	} else {
		var visibleDate = toXSDate(displayScheduleDate);
		jQuery.getJSON("/api/log?date=" + visibleDate, function(log) {
			for (var l in log) {
				log[l].duration = fromClock(log[l].duration);
				log[l].start = fromClock(log[l].start)/60;
				if (log[l].date != visibleDate) {
					log[l].start -= 24*60;
				}
				log[l].label = toClock(log[l].start, timeFormat) + " for " + toClock(log[l].duration, 1);
			}
			if (toXSDate(displayScheduleDate) == toXSDate(new Date(Date.now() + cliTzOffset - devTzOffset))) {
				var schedule = doSimulation(); //dk
				log = log.concat(schedule);
			}
			displaySchedule(log);
		})
	}
}

jQuery(document).ready(displayProgram);

function scheduleMarkerMouseover() {
	var description = jQuery(this).attr("data");
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


