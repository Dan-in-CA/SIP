// Javascript for printing OpenSprinkler option page 
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

var str_tooltips=["Example: GMT-4:00, GMT+5:30 (effective after reboot).", "HTTP port (effective after reboot).", "HTTP port (effective after reboot).", "Number of extension boards", "Sequential running or concurrent running", "Station delay time (in seconds), between 0 and 240.", "Select master station", "Master on delay (in seconds), between +0 and +60.", "Master off delay (in seconds), between -60 and +60.", "Use rain sensor", "Rain sensor type", "Water level, between 0% and 250%.", "Ignore web password"];
function w(s) {document.writeln(s);}
function imgstr(s) {return "<img src=\""+baseurl+"/static/images/icons/svc_"+s+".png\" height=20 align=absmiddle>&nbsp;";}
function submit_form(f) {
  // process time zone value
  var th=parseInt(f.elements["th"].value,10);
  var tq=parseInt(f.elements["tq"].value,10);
  tq=(tq/15>>0)/4.0;th=th+(th>=0?tq:-tq);
  // huge hack, needs to find a more elegant way
  f.elements["o1"].value=((th+12)*4)>>0;
  f.elements["o12"].value=(f.elements["htp"].value)&0xff;
  f.elements["o13"].value=(f.elements["htp"].value>>8)&0xff;
  f.elements["o18"].value=f.elements["mas"].value;
  f.submit();
}
function fcancel() {window.location="/";}
function fshow() {
  var oid,tip;
  for(oid=0;oid<nopts;oid++){
    tip=document.getElementById("tip"+oid);
    if(tip!=null) tip.hidden=false;
  }
}
w("<div align=\"center\" style=\"background-color:#EEEEEE;border:2px solid gray;padding:5px 10px;width:240px;border-radius:10px;box-shadow:3px 3px 2px #888888;\">");
w("<b>Set Options</b>:<br><font size=2>(Hover on each option to see tooltip)</font></div>");
w("<p></p>");
w("<button style=\"height:24\" onclick=\"fshow();return false;\">Show Tooltips</button>");
// print html form
w("<form name=of action=co method=get>");
var oid,name,isbool,value,index,pasoid=0;
for(oid=0;oid<nopts;oid++){
  name=opts[oid*4+0];
  isbool=opts[oid*4+1];
  value=opts[oid*4+2];
  index=opts[oid*4+3];
  if(name=="Ignore password:") pasoid=oid;
  if(isbool)  w("<p title=\""+str_tooltips[oid]+"\"><b>"+name+"</b> <input type=checkbox "+(value>0?"checked":"")+" name=o"+index+">");
  else {
    // hack
    if (name=="Time zone:") {
      w("<input type=hidden value=0 name=o"+index+">");
      tz=value-48;
      w("<p title=\""+str_tooltips[oid]+"\"><b>"+name+"</b> GMT<input type=text size=3 maxlength=3 value="+(tz>=0?"+":"-")+(Math.abs(tz)/4>>0)+" name=th>");
      w(":<input type=text size=3 maxlength=3 value="+((Math.abs(tz)%4)*15/10>>0)+((Math.abs(tz)%4)*15%10)+" name=tq>");
    } else if (name=="Master station:") {
      w("<input type=hidden value=0 name=o"+index+">");
      w("<p title=\""+str_tooltips[oid]+"\"><b>"+name+"</b> <select name=mas><option "+(value==0?" selected ":" ")+"value=0>None</option>");
      for(i=1;i<=8;i++) w("<option "+(value==i?" selected ":" ")+"value="+i+">Station 0"+i+"</option>");
      w("</select>");
    } else if (name=="HTTP port:") {
      w("<input type=hidden value=0 name=o"+index+"><input type=hidden value=0 name=o"+(index+1)+">");
      var port=value+(opts[(oid+1)*4+2]<<8);
      w("<p title=\""+str_tooltips[oid]+"\"><b>"+name+"</b> <input type=text size=5 maxlength=5 value="+port+" name=htp>");
      oid++;
    } 
    else {
      w("<p title=\""+str_tooltips[oid]+"\"><b>"+name+"</b> <input type=text size=3 maxlength=3 value="+value+" name=o"+index+">");
    }
  }
  //w("</p>");
  w(" <span style=\"background-color:#FFF2B8;\" id=tip"+oid+" hidden=\"hidden\"><font size=2>"+str_tooltips[oid]+"</font></span></p>");
}
w("<p title=\"City name or zip code. Use comma or + in place of space.\"><b>Location:</b> <input type=text maxlength=31 value=\""+loc+"\" name=loc></p>");
w("<h4>Password:<input type=password size=10 "+(opts[pasoid*4+2]?"disabled":"")+" name=pw></h4>");
w("<button style=\"height:36\" onclick=\"submit_form(of)\">"+imgstr("submit")+"<b>Submit Changes</b></button>");
w("<button style=\"height:36\" onclick=\"fcancel();return false;\">"+imgstr("delall")+"Cancel</button>");
w("<h4>Change password</b>:<input type=password size=10 name=npw>&nbsp;&nbsp;Confirm:&nbsp;<input type=password size=10 name=cpw></h4>");
w("</form>");
