// Javascript for printing OpenSprinkler option page 
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

function w(s) {document.writeln(s);}
function imgstr(s) {return "<img src=\""+baseurl+"/static/images/icons/svc_"+s+".png\" height=20 align=absmiddle>&nbsp;";}
function submit_form(f) {
  // process time zone value
  var th=parseInt(f.elements["th"].value,10);
  var tq=parseInt(f.elements["tq"].value,10);
  tq=(tq/15>>0)/4.0;
  th=th+(th>=0?tq:-tq);
  // huge hack, needs to find a more elegant way
  f.elements["otz"].value=((th+12)*4)>>0;
  f.elements["ohtp"].value=(f.elements["htp"].value)&0xff;
  f.elements["ohtp2"].value=(f.elements["htp"].value>>8)&0xff;
  //f.elements["omas"].value=f.elements["mas"].value;
  f.submit();
}
function fcancel() {window.location="/";}
function ftoggle() {
  var oid,tip;
  var state=document.getElementById("tip0").style.display=="none";
  for(oid=0;oid<opts.length;oid++){
    tip=document.getElementById("tip"+oid);
    if(tip!=null) tip.style.display=state?"inline":"none";
  }
  document.getElementById("tooltips").innerHTML = (state?"Hide Tooltips":"Show Tooltips");
}
w("<div align=\"center\" style=\"background-color:#EEEEEE;border:2px solid gray;padding:5px 10px;width:240px;border-radius:10px;box-shadow:3px 3px 2px #888888;\">");
w("<b>Set Options</b>:<br><font size=2>(Hover on each option to see tooltip)</font></div>");
w("<p></p>");
w("<button id=\"tooltips\" style=\"height:24\" onclick=\"ftoggle();return false;\">Show Tooltips</button>");
// print html form
w("<form name=of action=co method=get>");
var oid,label,isbool,value,name,ipasvalue=0;
for(oid=0;oid<opts.length;oid++){
  label=opts[oid][0];
  datatype=opts[oid][1];
  value=sd[opts[oid][2]];
  name=opts[oid][2];
  tooltip=opts[oid][3];
  if(name=="ipas") ipasvalue=value;
  if(datatype == "boolean") {
  	w("<p title=\""+tooltip+"\"><b>"+label+":</b> <input type=checkbox "+(value>0?"checked":"")+" name=o"+name+">");
  } else if (datatype == "string") {
    w("<p title=\""+tooltip+"\"><b>"+label+":</b> <input type=text size=31 maxlength=31 value='"+value+"' name=o"+name+">");
  } else {
    switch (name) {
    case "tz":
      w("<input type=hidden value=0 name=o"+name+">");
      tz=value-48;
      w("<p title=\""+tooltip+"\"><b>"+label+":</b> GMT<input type=text size=3 maxlength=3 value="+(tz>=0?"+":"-")+(Math.abs(tz)/4>>0)+" name=th>");
      w(":<input type=text size=3 maxlength=3 value="+((Math.abs(tz)%4)*15/10>>0)+((Math.abs(tz)%4)*15%10)+" name=tq>");
      break;
    case "mas":
      //w("<input type=hidden value=0 name=o"+name+">");
      w("<p title=\""+tooltip+"\"><b>"+label+":</b> <select name=o"+name+"><option "+(value==0?" selected ":" ")+"value=0>None</option>");
      for(i=1;i<=8;i++) w("<option "+(value==i?" selected ":" ")+"value="+i+">Station 0"+i+"</option>");
      w("</select>");
      break;
    case "htp":
      w("<input type=hidden value=0 name=o"+name+"><input type=hidden value=0 name=o"+name+"2>");
      var port=value+(opts[(oid+1)][2]<<8);
      w("<p title=\""+tooltip+"\"><b>"+label+":</b> <input type=text size=5 maxlength=5 value="+port+" name=ohtp>");
      break;
    case "nbrd":
      w("<p title=\""+tooltip+"\"><b>"+label+":</b> <input type=text size=3 maxlength=3 value="+(value-1)+" name=o"+name+">");
      break;
    default:
      w("<p title=\""+tooltip+"\"><b>"+label+":</b> <input type=text size=3 maxlength=3 value="+value+" name=o"+name+">");
    }
  }
  //w("</p>");
  w(" <span style=\"background-color:#FFF2B8;display:none\" id=tip"+oid+"><font size=2>"+tooltip+"</font></span></p>");
}
w("<h4>Password:<input type=password size=10 "+(ipasvalue?"disabled":"")+" name=pw></h4>");
w("<button style=\"height:36\" onclick=\"submit_form(of)\">"+imgstr("submit")+"<b>Submit Changes</b></button>");
w("<button style=\"height:36\" onclick=\"fcancel();return false;\">"+imgstr("delall")+"Cancel</button>");
w("<h4>Change password</b>:<input type=password size=10 name=npw>&nbsp;&nbsp;Confirm:&nbsp;<input type=password size=10 name=cpw></h4>");
w("</form>");
