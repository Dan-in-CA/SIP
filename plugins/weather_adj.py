#!/usr/bin/env python

import web, json, time
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs
try:
    from apscheduler.scheduler import Scheduler #This is a non-standard module. Needs to be installed in order for this feature to work.
except ImportError:
    print "The Python module apscheduler could not be found."
    pass

urls.extend(['/wa', 'plugins.weather_adj.settings', '/uwa', 'plugins.weather_adj.update']) # Add a new url to open the data entry page.

gv.plugin_menu.append(['Weather Adjust Settings', '/wa']) # Add this plugin to the home page plugins menu

try:
    sched = Scheduler()
    sched.start() # Start the scheduler
except NameError:
    pass

def weather_to_delay():
    data = get_weather_options()
    weather = get_weather_data() if weather_provider == "yahoo" else get_wunderground_weather_data()
    delay = code_to_delay(weather["code"])
    if delay === False return;
#    send_to_os("/cv?pw=&rd=".$delay); <-- convert to variable change in gv

def get_weather_options():
    try:
        f = open('./data/weather_adj.json', 'r') # Read the monthly percentages from file
        data = json.load(f)
        f.close()
    except Exception, e:
        data = {'auto_delay': 'off', 'delay_duration': 24, 'weather_provider': 'yahoo', 'wapikey': ''}

    return data

#Resolve location to LID
def get_wunderground_lid():
    $options = get_options();
    if (preg_match("/pws:/",$options["loc"]) == 1) {
        $lid = $options["loc"];
    } else {
        $data = file_get_contents("http://autocomplete.wunderground.com/aq?h=0&query=".urlencode($options["loc"]));
        $data = json_decode($data);
        if (empty($data)) return "";
        $lid = "zmw:".$data->{'RESULTS'}[0]->{'zmw'};
    }
    return $lid;

def get_weather_data():
    global $woeid;
    if (!$woeid) return array();
    $data = file_get_contents("http://weather.yahooapis.com/forecastrss?w=".$woeid);
    if ($data === false) return array();
    preg_match("/<yweather:condition\s+text=\"([\w|\s]+)\"\s+code=\"(\d+)\"\s+temp=\"(\d+)\"\s+date=\"(.*)\"/", $data, $newdata);
    preg_match("/<title>Yahoo! Weather - (.*)<\/title>/",$data,$loc);
    preg_match("/<yweather:location .*?country=\"(.*?)\"\/>/",$data,$region);
    $region = $region[1];
    if ($region == "United States" || $region == "Bermuda" || $region == "Palau") {
        $temp = $newdata[3]."&#176;F";
    } else {
        $temp = intval(round(($newdata[3]-32)*(5/9)))."&#176;C";
    }
    $weather = array("text"=>$newdata[1],"code"=>$newdata[2],"temp"=>$temp,"date"=>$newdata[4],"location"=>$loc[1]);
    return $weather;

def get_wunderground_weather_data():
    global $lang, $lid, $wapikey;
    if ($lid == "") return array();
    $data = file_get_contents("http://api.wunderground.com/api/".$wapikey."/conditions/q/".$lid.".json");
    if ($data === false) return array();
    $data = json_decode($data);
    if (isset($data->{'response'}->{'error'}->{'type'})) return array();
    $region = $data->{'current_observation'}->{'display_location'}->{'country_iso3166'};
    $temp_c = $data->{'current_observation'}->{'temp_c'};
    $temp_f = $data->{'current_observation'}->{'temp_f'};
    if ($region == "US" || $region == "BM" || $region == "PW") {
        $temp = round($temp_f)."&#176;F";
    } else {
        $temp = $temp_c."&#176;C";
    }
    if (strpos($data->{'current_observation'}->{'icon_url'},"nt_") !== false) { $code = "nt_".$data->{'current_observation'}->{'icon'}; }
    else $code = $data->{'current_observation'}->{'icon'};
    $weather = array("text"=>$data->{'current_observation'}->{'weather'}, "code"=>$code, "temp"=>$temp,"date"=>$data->{'current_observation'}->{'observation_time'}, "location"=>$data->{'current_observation'}->{'display_location'}->{'full'});
    return $weather;

#Lookup code and get the set delay
def code_to_delay(code):
    global $auto_delay_duration, $weather_provider;
    if ($weather_provider == "yahoo") {
        $adverse_codes = array(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,35,37,38,39,40,41,42,43,44,45,46,47);
        $reset_codes = array(36);
    } else {
        $adverse_codes = array("flurries","sleet","rain","sleet","snow","tstorms","nt_flurries","nt_sleet","nt_rain","nt_sleet","nt_snow","nt_tstorms");
        $reset_codes = array("sunny","nt_sunny");
    }
    if (in_array($code, $adverse_codes)) return $auto_delay_duration;
    if (in_array($code, $reset_codes)) return 0;
    return false;

class settings:
    """Load an html page for entering weather-based irrigation adjustments"""
    def __init__(self):
        self.render = web.template.render('templates/')

    def GET(self):
        return self.render.weather_adj(get_weather_options())

class update:
    """Save user input to weather_adj.json file"""
    def GET(self):
        qdict = web.input()
        if not qdict.has_key('auto_delay'):
            qdict['auto_delay'] = 'off'
        f = open('./data/weather_adj.json', 'w') # write the monthly percentages to file
        json.dump(qdict, f)
        f.close()
        raise web.seeother('/')

try:
    sched.add_cron_job(set_wl, hour=1) # Run the plugin's function the every hour
except NameError:
    pass
