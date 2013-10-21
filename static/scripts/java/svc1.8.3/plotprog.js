// Javascript for printing OpenSprinkler schedule page
// Firmware v1.8
// All content is published under:
// Creative Commons Attribution ShareAlike 3.0 License
// Sep 2012, Rayshobby.net

// colors to draw different programs
var prog_color=["rgba(0,0,200,0.5)","rgba(0,200,0,0.5)","rgba(200,0,0,0.5)","rgba(0,200,200,0.5)"];
var days_str=["Sun","Mon","Tue","Wed","Thur","Fri","Sat"];
var xstart=80,ystart=80,stwidth=40,stheight=180;
var winwidth=stwidth*sd['nbrd']*8+xstart, winheight=26*stheight+ystart;
var sid,sn,t;
var simt=Date.UTC(yy,mm-1,dd,0,0,0,0);
var simdate=new Date(simt);
var simday = (simt/1000/3600/24)>>0;
function w(s) {document.writeln(s);}
function check_match(prog,simminutes,simdate,simday) {
  // simdate is Java date object, simday is the #days since 1970 01-01
  var wd,dn,drem;
  if(prog[0]==0)  return 0;
  if ((prog[1]&0x80)&&(prog[2]>1)) {  // inverval checking
    dn=prog[2];drem=prog[1]&0x7f;
    if((simday%dn)!=((devday+drem)%dn)) return 0; // remainder checking
  } else {
    wd=(simdate.getUTCDay()+6)%7; // getDay assumes sunday is 0, converts to Monday 0
    if((prog[1]&(1<<wd))==0)  return 0; // weekday checking
    dt=simdate.getUTCDate(); // day of the month
    if((prog[1]&0x80)&&(prog[2]==0))  {if((dt%2)!=0)  return 0;} // even day checking
    if((prog[1]&0x80)&&(prog[2]==1))  { // odd day checking
      if(dt==31)  return 0;
      else if (dt==29 && simdate.getUTCMonth()==1) return 0;
      else if ((dt%2)!=1) return 0;
    }
  }
  if(simminutes<prog[3] || simminutes>prog[4])  return 0; // start and end time checking
  if(prog[5]==0)  return 0;
  if(((simminutes-prog[3])/prog[5]>>0)*prog[5] == (simminutes-prog[3])) { // interval checking
    return 1;
  }
  return 0;  // no match found
}
function getx(sid)  {return xstart+sid*stwidth-stwidth/2;}  // x coordinate given a station
function gety(t)    {return ystart+t*stheight/60;}  // y coordinate given a time
function getrunstr(start,end){ // run time string
  var h,m,s,str;
  h=start/3600>>0;m=(start/60>>0)%60;s=start%60;
  str=""+(h/10>>0)+(h%10)+":"+(m/10>>0)+(m%10)+":"+(s/10>>0)+(s%10);
  h=end/3600>>0;m=(end/60>>0)%60;s=end%60;
  str+="->"+(h/10>>0)+(h%10)+":"+(m/10>>0)+(m%10)+":"+(s/10>>0)+(s%10);
  return str;
} 
function plot_bar(sid,start,pid,end) { // plot program bar
  w("<div title=\""+snames[sid]+" ["+getrunstr(start,end)+"]\" align=\"center\" style=\"position:absolute;background-color:"+prog_color[(pid+3)%4]+";left:"+getx(sid)+"px;top:"+gety(start/60)+"px;border:0;width:"+stwidth+"px;height:"+((end-start)/60*stheight/60)+"px\">P"+pid+"</div>");
}
function plot_master(start,end) {  // plot master station
  w("<div title=\"Master ["+getrunstr(start,end)+"]\" style=\"position:absolute;background-color:#CCCC80;left:"+getx(sd['mas']-1)+"px;top:"+gety(start/60)+"px;border:0;width:"+stwidth+"px;height:"+((end-start)/60*stheight/60)+"px\"></div>");
  //if(sd['mas']==0||start==end)  return;
  //ctx.fillStyle="rgba(64,64,64,0.5)";
  //ctx.fillRect(getx(mas-1),gety(start/60),stwidth,(end-start)/60*stheight/60);
}
function plot_currtime() {
  w("<div style=\"position:absolute;left:"+(xstart-stwidth/2-10)+"px;top:"+gety(devmin)+"px;border:1px solid rgba(200,0,0,0.5);width:"+(winwidth-xstart+stwidth/2)+"px;height:0px;\"></div>");
}
function run_sched(simseconds,st_array,pid_array,et_array) { // run and plot schedule stored in array data
  var sid,endtime=simseconds;
  for(sid=0;sid<sd['nbrd']*8;sid++) {
    if(pid_array[sid]) {
      if(sd['seq']==1) { // sequential
        plot_bar(sid,st_array[sid],pid_array[sid],et_array[sid]);
        if((sd['mas']>0)&&(sd['mas']!=sid+1)&&(sd['mo'][sid>>3]&(1<<(sid%8))))
          plot_master(st_array[sid]+sd['mton'], et_array[sid]+sd['mtoff']);
        endtime=et_array[sid];
      } else { // concurrent
        plot_bar(sid,simseconds,pid_array[sid],et_array[sid]);
        // check if this station activates master
        if((sd['mas']>0)&&(sd['mas']!=sid+1)&&(sd['mo'][sid>>3]&(1<<(sid%8))))
          endtime=(endtime>et_array[sid])?endtime:et_array[sid];
      }
    }
  }
  if(sd['seq']==0&&sd['mas']>0) plot_master(simseconds,endtime);
  return endtime;
}
function draw_title() {
  w("<div align=\"center\" style=\"background-color:#EEEEEE;position:absolute;left:0px;top:10px;border:2px solid gray;padding:5px 0px;width:"+(winwidth)+"px;border-radius:10px;box-shadow:3px 3px 2px #888888;\"><b>Program Preview of</b>&nbsp;");
  w(days_str[simdate.getUTCDay()]+" "+(simdate.getUTCMonth()+1)+"/"+(simdate.getUTCDate())+" "+(simdate.getUTCFullYear()));
  w("<br><font size=2>(Hover over each colored bar to see tooltip)</font>");
  w("</div>");
}

function draw_grid() {
  // draw table and grid
  for(sid=0;sid<=sd['nbrd']*8;sid++) {
    sn=sid+1;
    if(sid<sd['nbrd']*8) w("<div style=\"position:absolute;left:"+(xstart+sid*stwidth-10)+"px;top:"+(ystart-15)+"px;width:"+stwidth+"px;height:20px;border:0;padding:0;\"><font size=2>S"+(sn/10>>0)+(sn%10)+"</font></div>");
    w("<div style=\"position:absolute;left:"+getx(sid)+"px;top:"+(ystart-10)+"px;border:1px solid gray;width:0px;height:"+(winheight-ystart+30)+"px;\"></div>");
  }
  // horizontal grid, time
  for(t=0;t<=24;t++) {
    w("<div style=\"position:absolute;left:"+(xstart-stwidth/2-15)+"px;top:"+gety(t*60)+"px;border:1px solid gray;width:15px;height:0px;\"></div>");
    w("<div style=\"position:absolute;left:"+(xstart-stwidth/2-8)+"px;top:"+(gety(t*60)+stheight/2)+"px;border:1px solid gray;width:8px;height:0px;\"></div>");
    w("<div style=\"position:absolute;left:"+(xstart-70)+"px;top:"+(ystart+t*stheight-7)+"px;width=70;height:20px;border:0;padding:0;\"><font size=2>"+(t/10>>0)+(t%10)+":00</font></div>");
  }
  plot_currtime();
}
function draw_program() {
  // plot program data by a full simulation
  var simminutes=0,busy=0,match_found=0,bid,s,sid,pid,match=[0,0];
  var st_array=new Array(sd['nbrd']*8),pid_array=new Array(sd['nbrd']*8);
  var et_array=new Array(sd['nbrd']*8);
  for(sid=0;sid<sd['nbrd']*8;sid++)  {
    st_array[sid]=0;pid_array[sid]=0;et_array[sid]=0;
  }
  do { // check through every program
    busy=0;
    match_found=0;
    for(pid=0;pid<nprogs;pid++) {
      var prog=pd[pid];
      if(check_match(prog,simminutes,simdate,simday)) {
        for(sid=0;sid<sd['nbrd']*8;sid++) {
          bid=sid>>3;s=sid%8;
          if(sd['mas']==(sid+1)) continue; // skip master station
          if(prog[7+bid]&(1<<s)) {
            et_array[sid]=prog[6]*sd['wl']/100>>0;pid_array[sid]=pid+1;
            match_found=1;
          }//if
        }//for_sid
      }//if_match
    }//for_pid
    if(match_found) {
      var acctime=simminutes*60;
      if(sd['seq']) { // sequential
        for(sid=0;sid<sd['nbrd']*8;sid++) {
          if(et_array[sid]) {
            st_array[sid]=acctime;acctime+=et_array[sid];
            et_array[sid]=acctime;acctime+=sd['sdt'];
            busy=1;
          }//if
        }//for
      } else {
        for(sid=0;sid<sd['nbrd']*8;sid++) {
          if(et_array[sid]) {
            st_array[sid]=simminutes*60;
            et_array[sid]=simminutes*60+et_array[sid];
            busy=1;
          }//if(et_array)
        }//for(sid)
      }//else(seq)
    }//if(match_found)
    if (busy) {
      var endminutes=run_sched(simminutes*60,st_array,pid_array,et_array)/60>>0;
      if(sd['seq']&&simminutes!=endminutes) simminutes=endminutes;
      else simminutes++;
      for(sid=0;sid<sd['nbrd']*8;sid++)  {st_array[sid]=0;pid_array[sid]=0;et_array[sid]=0;} // clear program data
    } else {
      simminutes++; // increment simulation time
    }
  } while(simminutes<24*60); // simulation ends
  window.scrollTo(0,gety((devmin/60>>0)*60)); // scroll to the hour line cloest to the current time
}

draw_title();
draw_grid();
draw_program();
