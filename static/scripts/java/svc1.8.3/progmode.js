// Javascript for printing OpenSprinkler homepage (program mode)
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

// print station status
function rsn() {
  var p="";
  if(!ipas) p=prompt("Please enter your password:","");
  if(p!=null) window.location="/cv?pw="+p+"&rsn=1";
}

w("<button style=\"height:32\" onclick=linkn(\"/gp?d=0\")>"+imgstr("preview")+"Program Preview</button>");
w("<button style=\"height:32\" onclick=rsn()>"+imgstr("del")+"Stop All Stations</button>");
w("<button style=\"height:32\" onclick=link(\"/vr\")>"+imgstr("start")+"Run-Once Program</button><br>");
w("<p><b>Station Status</b>:</p>");
w("<table border=1>");
var bid,s,sid,sn,rem,remm,rems,off,pname;
//off=((en==0||rd!=0||(urs!=0&&rs!=0))?1:0); // move rain stuff to after sid = ...
off=((en==0)?1:0); 
for(bid=0;bid<nbrd;bid++){
  for(s=0;s<8;s++){
    w("<tr><td bgcolor=\"#E4E4E4\">");
    sid=bid*8+s;
	 exempt=((ir[bid]&1<<s)?1:0);
	 if(en==1) {off=(((rd!=0||(urs!=0&&rs!=0))&&exempt!=1)?1:0);}
    sn=sid+1;
    w(snames[sid]+':&nbsp;&nbsp;');
    w("</td><td>");
    if(off) w("<strike>");
    if(sn==mas) {w(((sbits[bid]>>s)&1?("<b>On</b>").fontcolor("green"):("Off").fontcolor("black"))+" (<b>Master</b>)");}
    else {
      rem=ps[sid][1];remm=rem/60>>0;rems=rem%60;
      pname="P"+ps[sid][0];
      if(ps[sid][0]==255||ps[sid][0]==99) pname="Manual Program";
      if(ps[sid][0]==254||ps[sid][0]==98) pname="Run-once Program";
      if((sbits[bid]>>s)&1) {
        w(("<b>Running "+pname).fontcolor("green")+"</b> ("+(remm/10>>0)+(remm%10)+":"+(rems/10>>0)+(rems%10)+" remaining)");
      } else {
        if(ps[sid][0]==0) w("<font color=lightgray>(closed)</font>");
        else w(("Waiting "+pname+" ("+(remm/10>>0)+(remm%10)+":"+(rems/10>>0)+(rems%10)+" scheduled)").fontcolor("gray"));
      }
    }
    if(off) w("</strike>");
    w("</td></tr>");
  }
}
w("</table>");
