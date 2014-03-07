// Javascript for printing OpenSprinkler modify program page
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

function w(s) {document.writeln(s);}
function id(s){return document.getElementById(s);}
function imgstr(s) {return "<img src=\""+baseurl+"/static/images/icons/svc_"+s+".png\" height=20 align=absmiddle>&nbsp;";}
// parse time
function parse_time(prefix) {
	var h=parseInt(id(prefix+"h").value,10);
	var m=parseInt(id(prefix+"m").value,10);
	if(!(h>=0&&h<24&&m>=0&&m<60))	{alert("Error: Incorrect time input "+prefix+".");return -1;}
	return h*60+m;
}
// fill time
function fill_time(prefix,idx) {
	var t=prog[idx];
	id(prefix+"h").value=""+((t/60>>0)/10>>0)+((t/60>>0)%10);
	id(prefix+"m").value=""+((t%60)/10>>0)+((t%60)%10);
}
// check/uncheck all days
function seldays(v) {
  var i;
  for(i=0;i<7;i++) id("d"+i).checked=(v>0)?true:false;
}
// handle form submit
function fsubmit(f) {
  var errmsg = "",days=[0,0],i,s,sid;
  var en=0;
  if(id("en_on").checked) en=1;
	// process days
	if(id("days_week").checked) {
		for(i=0;i<7;i++) {if(id("d"+i).checked) {days[0] |= (1<<i);	}}
		if(id("days_odd").checked) {days[0]|=0x80; days[1]=1;}
		else if(id("days_even").checked) {days[0]|=0x80; days[1]=0;}
	} else if(id("days_n").checked) {
		days[1]=parseInt(id("dn").value,10);
		if(!(days[1]>=2&&days[1]<=128)) {alert("Error: interval days must be between 2 and 128.");return;}
		days[0]=parseInt(id("drem").value,10);
		if(!(days[0]>=0&&days[0]<days[1])) {alert("Error: starting in days wrong.");return;}
		days[0]|=0x80;
	}
	if(days[0]==0||(days[1]<2&&(days[0]&0x7f)==0)) {alert("Error: You have not selected any day.");return;}
	// process stations
	var stations=[0],station_selected=0,bid;
	for(bid=0;bid<sd['nbrd'];bid++) {
		stations[bid]=0;
		for(s=0;s<8;s++) {
			sid=bid*8+s;
			if(id("s"+sid).checked) {
				stations[bid] |= 1<<s; station_selected=1;
			}
		}
	}
	if(station_selected==0) {alert("Error: You have not selected any station.");return;}
	// process time
	var start_time,end_time,interval,duration;
	if((start_time=parse_time("ts")) < 0)	return;
	if((end_time=parse_time("te")) < 0)	return;
	if(!(start_time<end_time))	{alert("Error: Start time must be prior to end time.");return;}
	if((interval=parse_time("ti")) < 0)	return;
	var dm=parseInt(id("tdm").value,10);
	var ds=parseInt(id("tds").value,10);
	duration=dm*60+ds;
	if(!(dm>=0&&ds>=0&&ds<60&&duration>0))	{alert("Error: Incorrect duration.");return;}
  // password
  var p="";
  if(!sd['ipas']) p=prompt("Please enter your password:","");
	if(p!=null){
		f.elements[0].value=p;
		f.elements[1].value=pid;
		f.elements[2].value="["+en+","+days[0]+","+days[1]+","+start_time+","+end_time+","+interval+","+duration;
		for(i=0;i<sd['nbrd'];i++) {f.elements[2].value+=","+stations[i];}
		f.elements[2].value+="]";
		f.submit();
	}
}
// handle form cancel
function fcancel() {window.location="/vp";}
// print html form
w("<div style=\"padding-top:10px;padding-bottom:0px;\"><b>"+((pid>-1)?"Modify Program "+(pid+1):"Add a New Program")+"</b></div><hr>");
w("<form name=mf action=cp method=get><input type=hidden name=pw><input type=hidden name=pid><input type=hidden name=v>");
w("<div style=\"padding-left:5px;padding-right:5px;\">");
w("<p><b>This program is: </b><input type=radio name=rad_en id=en_on><b>On</b><input type=radio name=rad_en id=en_off><b>Off</b></p>");
w("<p><b>Select Days:</b></p><input type=radio name=rad_day id=days_week><b><u>Weekly</u>:</b><input type=checkbox id=d0>Mon<input type=checkbox id=d1>Tue<input type=checkbox id=d2>Wed<input type=checkbox id=d3>Thu<input type=checkbox id=d4>Fri<input type=checkbox id=d5>Sat<input type=checkbox id=d6>Sun<br>")
w("<div style=\"padding-left:80px;\"><button onclick=\"seldays(1);return false;\">Select All</button><button onclick=\"seldays(0);return false;\">Select None</button></div>");
w("<div style=\"padding-left:20px;\"><p><b>Select Restrictions:</b><br><input type=radio name=rad_rst id=days_norst>No restriction<br><input type=radio name=rad_rst id=days_odd>Odd days only (except 31st and Feb 29th)<br><input type=radio name=rad_rst id=days_even>Even days only<br></p></div>");
w("<input type=radio name=rad_day id=days_n><b><u>Interval</u>:</b> Every <input type=text size=2 maxlength=2 id=dn> days, starting in <input type=text size=2 maxlength=2 id=drem> days.<hr>");
w("<p><b>Select Stations:</b></p>");
w("<table border=1 cellpadding=3>");
var bid,s,sid;
for(bid=0;bid<sd['nbrd'];bid++) {
  for(s=0;s<8;s++) {
    sid=bid*8+s;
    if(sid%4==0) w("<tr>");
    w("<td>");
    w("<input type=checkbox id=s"+sid+">"+snames[sid]);
    w("</td>");
    if(sid%4==3) w("</tr>");
  }
}
w("</table><p></p><hr>");
w("<p></p><b>Time:</b> <input type=text size=2 maxlength=2 id=tsh> : <input type=text size=2 maxlength=2 id=tsm> -> <input type=text size=2 maxlength=2 id=teh> : <input type=text size=2 maxlength=2 id=tem> (hh:mm)<br><b>Every:</b> <input type=text size=2 maxlength=2 id=tih> hours <input type=text size=2 maxlength=2 id=tim> minutes <br><b>Duration:</b> <input type=text size=2 maxlength=3 id=tdm> minutes <input type=text size=2 maxlength=2 id=tds> seconds<p></p><hr>");
w("</div></form>");
w("<button style=\"height:36\" onclick=\"fsubmit(mf)\">"+imgstr("submit")+"<b>Submit</b></button>");
w("<button style=\"height:36\" onclick=\"fcancel()\">"+imgstr("delall")+"Cancel</button>");
// default values
id("en_on").checked=true;
id("days_week").checked=true;id("days_norst").checked=true;
id("dn").value="3";id("drem").value="0";
id("tsh").value="06";id("tsm").value="00";id("teh").value="18";id("tem").value="00";
id("tih").value="04";id("tim").value="00";id("tdm").value="15";id("tds").value="00";
// fill in existing program values
if(pid>-1) {
  if(prog[0]==0) id("en_off").checked=true;
	// process days
	var _days=[prog[1],prog[2]];
	if((_days[0]&0x80)&&(_days[1]>1)) {
		id("days_n").checked=true;
		id("dn").value=_days[1];id("drem").value=_days[0]&0x7f;
	} else {
		id("days_week").checked=true;
		for(i=0;i<7;i++) {if(_days[0]&(1<<i))	id("d"+i).checked=true;}
		if((_days[0]&0x80)&&(_days[1]==0))	{id("days_even").checked=true;}
		if((_days[0]&0x80)&&(_days[1]==1))	{id("days_odd").checked=true;}
	}
	// process time
	fill_time("ts",3);
	fill_time("te",4);
	fill_time("ti",5);
	var t=prog[6];
	id("tdm").value=""+((t/60>>0)/10>>0)+((t/60>>0)%10);
	id("tds").value=""+((t%60)/10>>0)+((t%60)%10);
	// process stations
	var bits;
	for(bid=0;bid<sd['nbrd'];bid++) {
		bits=prog[bid+7];
		for(s=0;s<8;s++) {sid=bid*8+s;id("s"+sid).checked=(bits&(1<<s)?true:false);}
	}
}
