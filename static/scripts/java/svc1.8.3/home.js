// Javascript for printing OpenSprinkler homepage
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

function w(s) {document.writeln(s);}
function link(s) {window.location=s;}
function linkn(s){window.open(s, '_blank');}
// input rain delay value
function setrd(form,idx) {var h=prompt("Enter hours to delay","0");if(h!=null){form.elements[idx].value=h;form.submit()};}
function imgstr(s) {return "<img src=\""+baseurl+"/static/images/icons/svc_"+s+".png\" height=20 align=absmiddle>&nbsp;";}
function datestr(t) {var _t=tz-48; return (new Date(t)).toUTCString()+((_t>=0)?"+":"-")+(Math.abs(_t)/4>>0)+":"+((Math.abs(_t)%4)*15/10>>0)+((Math.abs(_t)%4)*15%10);}
// raspi CPU temp unit
function toggle(form) {form.elements[0].value=tempunit;form.submit();}
w("<form name=tt action=ttu method=get><input type=hidden name=tunit></form>");
function bluebg(heat){
heat.style.backgroundColor='lightblue';}
function nobg(heat){
heat.style.backgroundColor='transparent';}

// print menu links
w("<button style=\"height:44\" onclick=link(\"/\")>"+imgstr("reset")+"Refresh</button>");
w("<button style=\"height:44\" onclick=link(\"/vo\")>"+imgstr("options")+"Options</button>");
w("<button style=\"height:44\" onclick=link(\"/vs\")>"+imgstr("edit")+"Stations</button>");
w("<button style=\"height:44\" onclick=link(\"/vp\")>"+imgstr("cal")+"Programs</button>");
//w("<button style=\"height:44\" onclick=linkn(\"http://igoogle.wunderground.com/cgi-bin/findweather/getForecast?query="+loc+"\")>"+imgstr("weather")+"Weather</button><p></p>");
w("<button style=\"height:44\" onclick=link(\"/vl\")>"+imgstr("log")+"Log</button><p></p>");
// print device information
if(ver>=100) w("<b>Firmware version</b>: "+(ver/100>>0)+"."+((ver/10>>0)%10)+"."+(ver%10)+"<br>");
else w("<b>Firmware version</b>: "+(ver/10>>0)+"."+(ver%10)+"<br>");
w("<b>Device time</b>: "+datestr(devt*1000)+"<br>");

if (typeof cputemp === 'undefined') cputemp="";
w("<b>CPU Temp</b>: <span id='heat' onmouseover='bluebg(this)' onmouseout='nobg(this)' style='cursor:pointer' onclick='toggle(tt)' title='Click to toggle Celsius <> Fahrenheit'>"+cputemp+"&deg;"+tempunit+"</span><hr>");
w("<script type=\"text/javascript\" src=\""+baseurl+"/static/scripts/java/svc1.8.3/"+((mm)?"manualmode.js":"progmode.js")+"\"></script>");
// print status and other information
w("<br><b>Operation</b>: "+(en?("on").fontcolor("green"):("OFF").fontcolor("red")));
w("<br><b>Raindelay</b>: "+(rd?("ON").fontcolor("red")+" (till "+datestr(rdst*1000)+")":("off").fontcolor("black")));
w("<br><b>Rainsense</b>: "+(urs?(rs?("Rain Detected").fontcolor("red"):("no rain").fontcolor("green")):"<font color=gray>n/a</font>"));
w("<br><b>Water level</b>: <font color="+((wl==100)?"green":"red")+">"+wl+"\%</font>");
var lrsid=lrun[0],lrpid=lrun[1],lrdur=lrun[2],lret=lrun[3];
var pname="P"+lrpid;
if(lrpid==255||lrpid==99) pname="Manual Mode";
if(lrpid==254||lrpid==98) pname="Run-once Program";
dstr=(new Date(lret*1000)).toUTCString().replace(" GMT","");
if(lrpid!=0) w("<br><b>Log</b>: "+(snames[lrsid]+" ran "+pname+" for "+(lrdur/60>>0)+"m"+(lrdur%60)+"s @ "+dstr).fontcolor("gray"));
else w("<br><b>Log</b>: <font color=gray>n/a</font>");
w("<hr>");
// print html form
w("<form name=hf action=cv method=get><p>Password:<input type=password "+(ipas?"disabled":"")+" size=10 id=pwd name=pw></p>");
w("<input type=hidden name=en><input type=hidden name=rd value=0><input type=hidden name=rbt value=0><input type=hidden name=mm value=0></form>");
w("<button style=\"height:36\" onclick=\"hf.elements[1].value="+(1-en)+";hf.submit();\">"+imgstr(en?"stop":"start")+(en?"Stop Operation":"Start Operation")+"</button>");
w("<button style=\"height:36\" onclick=\"hf.elements[4].value="+(1-mm)+";hf.submit();\">"+imgstr(mm?"auto":"manual")+(mm?"Manual Off":"Manual On")+"</button>");
w("<button style=\"height:36\" onclick=\"setrd(hf,2)\">"+imgstr("rain")+"Rain Delay</button>");
w("<button style=\"height:36\" onclick=\"hf.elements[3].value=1;hf.submit();\">"+imgstr("reboot")+"Reboot</button>");
w("<p></p><hr><br>");
