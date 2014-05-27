// Javascript for changing OpenSprinkler station names and master operation bits
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

function w(s) {document.writeln(s);}
function imgstr(s) {return "<img src=\""+baseurl+"/static/images/icons/svc_"+s+".png\" height=20 align=absmiddle>&nbsp;";}
function rst() {
  var sid,sn;
  for(sid=0;sid<sd['nbrd']*8;sid++) {
    sn=sid+1;
    console.log(sn)
    if (document.getElementById("n"+sid)== null) {
    	continue;
    }	
    document.getElementById("n"+sid).value="S"+(sn/10>>0)+(sn%10);
  }
}
function fsubmit(f) {
  if(sd['mas']>0) {
    var s, bid, sid;
    for(bid=0;bid<sd['nbrd'];bid++) {
      var vm=0;
      for(s=0;s<8;s++){
        sid=bid*8+(7-s);
        vm=vm<<1;
        if(sid+1==sd['mas']) {vm=vm+1;continue;}
        if(document.getElementById("mc"+sid).checked) {
          vm=vm+1;
        }
      }
      f.elements["m"+bid].value=vm;
    }
	}
    var vi;	
    for(bid=0;bid<sd['nbrd'];bid++) {
      vi=0;
      for(s=0;s<8;s++){
       sid=bid*8+(7-s);
		 vi=vi<<1;	
	   if(sid+1==sd['mas']) {vi=vi+1;continue;}  
      if(document.getElementById("rc"+sid).checked) {
          vi=vi+1;
        }	     		
      }
	   f.elements["i"+bid].value=vi;
	}
  f.submit();
}
function fcancel() {window.location="/";}
w("<div align=\"center\" style=\"background-color:#EEEEEE;border:2px solid gray;padding:5px 10px;width:240px;border-radius:10px;box-shadow:3px 3px 2px #888888;\">");
w("<font size=3><b>Set Stations:</b></font><br>");
w("<font size=2>(Maximum name length is "+sd['snlen']+" letters).</font></div><p></p>");
var sid,sn,bid,s;
w("<form name=sf action=cs method=get>");
w("<table><tr><th>Station</th><th>Name</th><th>Ignore Rain?</th>" + (sd['mas']>0?"<th>Activate Master?</th>":"") + "</tr>");
for(sid=0;sid<sd['nbrd']*8;sid++) {
  sn=sid+1;
  bid=sid>>3;
  s=sid%8;
  w("<tr><td>"+(sn/10>>0)+(sn%10)+"</td>");
  if (sid+1==sd['mas']) {
  	w("<td colspan=2>--Master--</td>");
  } else {
  	w("<td><input type=text size="+sd['snlen']+" maxlength="+sd['snlen']+" value=\""+snames[sid]+"\" name=s"+sid+" id=n"+sid+"></td>");
    if (sid+1!=sd['mas']) {
    	w("<td><input type=checkbox "+(sd['ir'][bid]&(1<<s)?"checked":"")+" id=rc"+sid+"></td>");
  	}
  	if (sd['mas']>0) w("<td><input type=checkbox "+(sd['mo'][bid]&(1<<s)?"checked":"")+" id=mc"+sid+"></td>");
  }
  w("</tr>");
}
w("</table>");
//w("<p>Note: preface a station name with \"~\" to indicate that it is disconnected and hide it in the interface.</p>");
w("<hr><font size=3><b>Password:</b><input type=password size=10 "+(sd['ipas']?"disabled":"")+" name=pw></font><p></p>");
for(bid=0;bid<sd['nbrd'];bid++) {
  w("<input type=hidden name=i"+bid+">");
  w("<input type=hidden name=m"+bid+">");
}
w("</form>");
w("<button style=\"height:36\" onclick=\"fsubmit(sf)\">"+imgstr("submit")+"<b>Submit Changes</b></button>");
w("<button style=\"height:36\" onclick=\"rst()\">"+imgstr("reset")+"Reset Names</button>");
w("<button style=\"height:36\" onclick=\"fcancel()\">"+imgstr("delall")+"Cancel</button>");
