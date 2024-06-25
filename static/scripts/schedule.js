// Global vars
var displayScheduleDate = new Date(Date.now() + tzDiff);
var displayScheduleTimeout;
var sid,sn,t;
if (typeof progs !== 'undefined'){var nprogs = progs.length}; // number of programs
if (typeof nbrd !== 'undefined'){var nst = nbrd*8}; // number of stations

function scheduledThisDate(pd,simminutes,simdate) { // check if progrm is scheduled for this date (displayScheduleDate) called from doSimulation
  // simminutes is minute count generated in doSimulation()
  // simdate is a JavaScript date object
  var wd;
  if(pd['enabled']==0)  return 0; // program not enabled, do not match
  if(pd['type'] == 'interval') { // if interval program... 
	// Create a date object representing the requested display date starting at midnight
	var dateToSim = new Date(simdate);
	dateToSim.setHours(0);
	dateToSim.setMinutes(0);
	dateToSim.setSeconds(0);
	// Calculate a unique day count since the start of the epoch, this must match days_since_epoch()
	// as it would be calculated on the device for the day
	var simday = Math.floor(dateToSim.valueOf()/(24*60*60*1000));
	if((simday % pd['interval_base_day']) != pd['day_mask'])
		return 0; // return if this day offset doesn't match the remainder
  } else { // Not interval 
    wd=(simdate.getDay()+6)%7; // getDay assumes sunday is 0, converts to Monday is 0 (weekday index)
    if((pd['day_mask']&(1<<wd))==0) return 0; // weekday checking  
//    	console.log('weekday did not match');  
    dt=simdate.getDate(); // set dt = day of the month
    if(pd['type'] == 'evendays') { // even day checking...
//    	console.log('even days did not match');
    	if(dt%2) return 0; // if odd day (dt%2 == 1), do not match
    }
    if(pd['type'] == 'odddays')  { // odd day checking...	
      if(dt==31) return 0; // if 31st of month, do not match
      else if (dt==29 && simdate.getMonth()==1) return 0; // if leap year day, do not match
//      console.log('odd days did not match');      
      else if (!(dt%2)) return 0; // if even day, do not match
    }
  }
  if(simminutes<pd['start_min'] || simminutes>=pd['stop_min']) return 0; // if simulated time is before start time or after stop time, do not match
  
  if((pd['cycle_min']==0)  
     && (simminutes == pd['start_min'])) {
   return 1;
  }
  else if((pd['cycle_min']!=0)
     && ((simminutes-pd['start_min'])/pd['cycle_min']>>0)*pd['cycle_min'] == (simminutes-pd['start_min'])) { // if programmed to run now...
  return 1; // scheduled for displayScheduleDate
  } 
  return 0;  // no match found
}

function doSimulation(simdate) { // Create schedule by a full program simulation, was draw_program()
  var simminutes=0;
  var busy=0,match_found=0,endmin=0,bid,s,sid,pid;
  var st_array=new Array(nst); //start time per station in seconds (since midnight)?
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
      var pd=progs[pid]; //progs=program array, pd=program element at this index (program data)
//      console.log("pd: " + JSON.stringify(pd));
      if(scheduledThisDate(pd,simminutes,simdate)) { //call scheduledThisDate function, if scheduled...
        for(sid=0;sid<nst;sid++) { //for each station...
          bid=sid>>3;s=sid%8; //set board index (bid) and station number per board (s) from station index (sid) 
          if(mas==(sid+1)) continue; // skip master station
          if((pd['station_mask'][bid])&(1<<s)) { // if this station is selected in this program...
        	  if(!idd==1) { //not individual station times
        	   var duration=pd['duration_sec'][0]; // get the program duration
        	  } else {var duration=pd['duration_sec'][sid];
        	  }  //get the station duration
            et_array[sid]=duration; // Set duration for this station
            if (iw[bid]&(1<<s) == 0) { // adjust duration by water level
              et_array[sid] *= wl/100*wlx/100;
            }
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
            et_array[sid]+=simminutes*60; // set end time for this station to end time shifted by start time
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
                        program: progs[pid_array[sid]-1].name, // program name
						program_index: pid_array[sid], //program number
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
 // console.log('schedule: ' + JSON.stringify(schedule))
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
	if(typeof p === 'string' || p instanceof String) { // it's a string
		if (p == "Manual" || p == "Run-once" || p == "Node-red") {
			return p + " Program";
		}	
		else if(!isNaN(p)) { // If p contains a number
			return "Program " + p
		}
		else {
			return p;
		}
	}
}

// show timeline on home page
function displaySchedule(schedule) {
	if (displayScheduleTimeout != null) {
		clearTimeout(displayScheduleTimeout);
	}
	var now = new Date(Date.now() + tzDiff);
	var nowMark = now.getHours()*60 + now.getMinutes();
	var isToday = toXSDate(displayScheduleDate) == toXSDate(now);
	var programsUsed = new Object();
	jQuery(".stationSchedule .scheduleTick").each(function() {
		jQuery(this).empty();
		var sid = jQuery(this).parent().attr("data");
		var slice = parseInt(jQuery(this).attr("data"))*60;
		var boxes = jQuery("<div class='scheduleMarkerContainer'></div>");
		for (var s in schedule) {
			if(schedule[s].program === "" || schedule[s].program === "Unnamed") {
				schedule[s].program = "program " + schedule[s].program_index.toString();
			}			
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
						var idx;						
						if (schedule[s].program_index == 99 || schedule[s].program_index == 98) {
							programClass = "programManual";						
						} else {
							programClass = "program" + (parseInt(schedule[s].program_index))%10;
						}
						programsUsed[schedule[s].program] = programClass;
						var markerClass = (schedule[s].date == undefined ? "schedule" : "history");
						boxes.append("<div class='scheduleMarker " + programClass + " " + markerClass + "' style='left:" + barStart*100 + "%;width:" + barWidth*100 + "%' title='" + programName(schedule[s].program) + ": " + schedule[s].label + "'></div>");
					}
				}
			}
		}
		if (isToday && slice <= nowMark && nowMark < slice+60) {
			var stationOn = jQuery(this).parent().children(".stationStatus").hasClass("station_on");
			boxes.append("<div class='nowMarker" + (stationOn?" on":"")+ "' style='width:2px;left:"+ Math.round((nowMark-slice)/60*(this.clientWidth-2)) + "px;'>");
		}
		if (boxes.children().length > 0) {
			jQuery(this).append(boxes);
		}
	});
	jQuery("#legend").empty();
	for (var p in programsUsed) {
		jQuery("#legend").append("<span class='" + programsUsed[p] + "'>" + programName(p) + "</span>");
	}
	
	jQuery("#displayScheduleDate").text(dateString(displayScheduleDate) + (displayScheduleDate.getFullYear() == now.getFullYear() ? "" : ", " + displayScheduleDate.getFullYear()));
	if (isToday) {
		displayScheduleTimeout = setTimeout(displayProgram, 1*60*1000);  // every minute
	}
}

function displayProgram() { // Controls home page irrigation timeline
	if (toXSDate(displayScheduleDate) > toXSDate(new Date(Date.now() + tzDiff))) { 
		// run the schedule for yesterday to see if anything is spilling over into today
		var yesterdaysSchedule = doSimulation(new Date(displayScheduleDate.getTime() - 24*60*60*1000));
		var spillOvers = [];
		for (var s in yesterdaysSchedule) {
			if (yesterdaysSchedule[s].start + yesterdaysSchedule[s].duration/60 > 1440) {
				//Found a program hanging over from yesterday
				spillOvers.push({
					program : yesterdaysSchedule[s].program,
					program_index : yesterdaysSchedule[s].program_index,
					station : yesterdaysSchedule[s].station,
					start : 0,
					duration : yesterdaysSchedule[s].duration - (1440-yesterdaysSchedule[s].start)*60,
					label : yesterdaysSchedule[s].label
				});
			}
		}
		var schedule = doSimulation(displayScheduleDate);
		displaySchedule(schedule.concat(spillOvers));
	} else {
		let visibleDate = toXSDate(displayScheduleDate);
		jQuery.getJSON("/api/log?date=" + visibleDate, function(log) {
			for (let l in log) {
				log[l].duration = fromClock(log[l].duration);
				log[l].start = fromClock(log[l].start)/60;
				recorded_log_start = log[l].start;  // Save original value for label
				if (log[l].date != visibleDate) {
					log[l].start -= 24*60;
				}
				if (log[l].program_index == undefined) { // previous log versions only record name, recreate the program_index
					if (log[l].program == "Run-once") log[l].program_index = 98;
					else if (log[l].program == "Manual") log[l].program_index = 99;
					else {
						log[l].program_index = progNames.indexOf(log[l].program);
						// Note this could give the wrong name if programs have been deleted since the log entry was generated,
						// but the effects of this will be minimal and the old log entry will eventually expire anyway.
					}
				}
				log[l].label = toClock(recorded_log_start, timeFormat) + " for " + toClock(log[l].duration/60, 1);
				if (log[l].adjustment != undefined && log[l].adjustment != "100") {
					log[l].label += " (adjusted " + log[l].adjustment + "%)";
				}
			}
			if (toXSDate(displayScheduleDate) == toXSDate(new Date(Date.now() + tzDiff))) {
				var schedule = doSimulation(displayScheduleDate); //dk
				log = log.concat(schedule);
			}
			displaySchedule(log);
		})
	}
}

jQuery(document).ready(displayProgram);

