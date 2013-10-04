// Javascript for printing OpenSprinkler schedule page
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Rayshobby.net, Sep 2012

var str_days=["Mon","Tue","Wed","Thur","Fri","Sat","Sun"];
function w(s) {document.writeln(s);}
function imgstr(s) {return "<img src=\""+baseurl+"/static/images/icons/svc_"+s+".png\" height=20 align=absmiddle>&nbsp;";}
function del(form,idx) {
  var p="";
  if(!sd['ipas']) p=prompt("Please enter your password:","");
  if(p!=null){form.elements[0].value=p;form.elements[1].value=idx;form.submit();}
}
function mod(form,idx) {form.elements[0].value=idx;form.submit();}

function rnow(form,idx) {
  //form.elements[0].value=idx;form.submit();
  var p="";
  if(!ipas) p=prompt("Please enter your password:","");
  if(p!=null){form.elements[0].value=p;form.elements[1].value=idx;form.submit();}
}

// parse and print days
function pdays(days){
  if((days[0]&0x80)&&(days[1]>1)){
    // this is an interval program 
    days[0]=days[0]&0x7f;
    w("Every "+days[1]+" days, starting in "+days[0]+" days.");
  } else {
    // this is a weekly program 
    for(d=0;d<7;d++) {if(days[0]&(1<<d)) {w(str_days[d]);}}
    if((days[0]&0x80)&&(days[1]==0))  {w("(Even days only)");}
    if((days[0]&0x80)&&(days[1]==1))  {w("(Odd days only)");}
  }
}
// parse and print stations
function pstations(data){
  w("<table border=1 cellpadding=3px>");
  var bid,s,bits,sid;
  for(bid=0;bid<sd['nbrd'];bid++){
    bits=data[bid+7];
    for(s=0;s<8;s++){
      sid=bid*8+s;
      if(sid%4==0) w("<tr>");
      w("<td style=\"background-color:");
      if(bits&(1<<s)) w("#9AFA9A\"><font size=2 color=black>"+snames[sid]);
      else w("white\"><font size=2 color=lightgray>"+snames[sid]);
      w("</font></td>");
      if(sid%4==3) w("</tr>");
    }
  } 
  w("</table>\n");
}
function fcancel() {window.location="/";}
function fplot() {window.open("/gp?d=0","_blank");}
w("<form name=df action=dp method=get><input type=hidden name=pw><input type=hidden name=pid></form>");
w("<form name=rn action=rp method=get><input type=hidden name=pw><input type=hidden name=pid></form>");
w("<form name=mf action=mp method=get><input type=hidden name=pid></form>");
w("<button style=\"height:44\" onclick=\"fcancel()\">"+imgstr("back")+"Back</button>");
w("<button style=\"height:44\" onclick=\"mod(mf,-1)\">"+imgstr("addall")+"<b>Add a New Program</b></button>");
w("<button style=\"height:44\" onclick=\"del(df,-1)\">"+imgstr("delall")+"Delete All</button>");
w("<button style=\"height:44\" onclick=\"fplot()\">"+imgstr("preview")+"Preview</button><hr>");
w("<b>Total number of programs: "+nprogs+" (maximum is "+sd['mnp']+")</b><br>");
// print programs
var pid,st,et,iv,du,sd;
for(pid=0;pid<nprogs;pid++) {
  w("<span style=\"line-height:22px\">");
  if(pd[pid][0]==0) w("<strike>");
  w("<br><b>Program "+(pid+1)+": ");
  // parse and print days
  pdays([pd[pid][1],pd[pid][2]]);
  w("</b>");
  if((pd[pid][0]&0x01)==0) w("</strike><font color=red>(Disabled)</font>");
  // print time
  st=pd[pid][3];
  et=pd[pid][4];
  iv=pd[pid][5];
  du=pd[pid][6];
  w("<br><b>Time</b>: "+((st/60>>0)/10>>0)+((st/60>>0)%10)+":"+((st%60)/10>>0)+((st%60)%10));
  w(" - "+((et/60>>0)/10>>0)+((et/60>>0)%10)+":"+((et%60)/10>>0)+((et%60)%10));
  w(",<b> Every</b> "+(iv/60>>0)+" hrs "+(iv%60)+" mins,");
  w("<br><b>Run</b>: "+(du/60>>0)+" mins "+(du%60)+" secs.<br>");
  // parse and print stations
  pstations(pd[pid]);
  w("</span>");
  // print buttons
  w("<br><button style=\"height:28\" onclick=del(df,"+pid+")>Delete</button>");
  w("<button style=\"height:28\" onclick=mod(mf,"+pid+")>Modify</button>");
  w("<button style=\"height:28\" onclick=rnow(rn,"+pid+")>Run Now</button>");
  w("<hr>");
}
