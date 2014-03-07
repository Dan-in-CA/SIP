// Javascript for printing OpenSprinkler Run Once page
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

function w(s) {document.writeln(s);}
function imgstr(s) {return "<img src=\""+baseurl+"/static/images/icons/svc_"+s+".png\" height=20 align=absmiddle>&nbsp;";}
function rst(f) {
  var sid,sn;
  for(sid=0;sid<sd['nbrd']*8;sid++) {
    if(sid+1==sd['mas'])  continue;
    f.elements["mm"+sid].value=0;
    f.elements["ss"+sid].value=0;
  }
}
function fsubmit(f) {
  var comm="/cr?pw="+(sd['ipas']?"":f.elements["pw"].value)+"&t=[";
  var sid,strmm,strss,mm,ss,matchfound=0;
  for(sid=0;sid<sd['nbrd']*8;sid++) {
    if(sid+1==sd['mas']) {comm+="0,";continue;}
    strmm=f.elements["mm"+sid].value;
    strss=f.elements["ss"+sid].value;
    mm=(strmm=="")?0:parseInt(strmm);
    ss=(strss=="")?0:parseInt(strss);
    if(!(mm>=0&&ss>=0&&ss<60))  {alert("Timer values wrong: "+strmm+":"+strss);return;}
    if(mm*60+ss>0) matchfound=1;
    comm+=(mm*60+ss)+",";
  }
  comm+="0]"
  if(!matchfound) {alert("No station is schedule to run");return;}
  window.location=comm;
}
function fcancel() {window.location="/";}
w("<div align=\"center\" style=\"background-color:#EEEEEE;border:2px solid gray;padding:5px 10px;width:240px;border-radius:10px;box-shadow:3px 3px 2px #888888;\">");
w("<font size=3><b>Run-Once Program:</b></font></div><p></p>");
var sid;
w("<table border=1>");
w("<form name=rf action=cr method=get>");
for(sid=0;sid<sd['nbrd']*8;sid++) {
  w("<tr><td bgcolor=\"#E4E4E4\">");
  w(snames[sid]+":&nbsp;&nbsp;</td><td>");
  if (sid+1==sd['mas']) {w("(<b>Master</b>)<br>");continue;}
  w("<input type=text size=3 maxlength=3 value=0 name=mm"+sid+">:");
  w("<input type=text size=2 maxlength=2 value=0 name=ss"+sid+"> (mm:ss)<br>");
  w("</td>");
}
w("</table>");
w("<hr><font size=3><b>Password:</b><input type=password size=10 "+(sd['ipas']?"disabled":"")+" name=pw></font><p></p>");
w("</form></span>");
w("<button style=\"height:36\" onclick=\"fsubmit(rf)\">"+imgstr("submit")+"<b>Run Now</b></button>");
w("<button style=\"height:36\" onclick=\"rst(rf)\">"+imgstr("reset")+"Reset Time</button>");
w("<button style=\"height:36\" onclick=\"fcancel()\">"+imgstr("delall")+"Cancel</button>");
