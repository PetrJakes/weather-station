#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
sending weather data from 
to:
- wunderground
- windguru
- windfinder
"""
import configparser
config = configparser.ConfigParser()
import time
import urllib
import logging
import logging.handlers as handlers
import ConfigParser
from datetime import datetime
import hashlib
import bme280

config.read('weather.ini')

settings = config['SETTINGS']
LOG_FILE = settings["LOG_FILE"]

windFinder = config["WINDFINDER"]
windGuru = config["WINDGURU"]
wUnderground = config["WEATHERUNDERGROUND"]

FORMAT = "%(asctime)s %(levelname)s %(message)s "
logger = logging.getLogger("weatherd")
logger.setLevel(logging.INFO)
handler = handlers.RotatingFileHandler(LOG_FILE, mode='a', maxBytes=10000, backupCount=3)
formatter = logging.Formatter(FORMAT, "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

# ************************
#       WINDFINDER
# ************************
# https://www.windfinder.com/report/phan-rang-kite-center_my-hoa
#
# Upload request example:
# http://www.windfinder.com/wind-cgi/httpload.pl?sender_id=phan-rang-kite-center_my-hoa&password=f47d4b810c1cc74b&date=19.5.2011&time=17:13&airtemp=20&windspeed=12&gust=14&winddir=180&pressure=1012&rain=5
#
# sender_id:    phan-rang-kite-center_my-hoa
# password:     f47d4b810c1cc74b
# date:         Local Date (DD.MM.YYYY e.g. 1.9.2017 or 24.10.2017)
# time:         Local Time (HH:MM)
# airtemp:      Air temp (Celsius, C°)
# windspeed:    Wind speed (knots)
# gust:         Wind speed (knots)
# winddir:      Wind direction (degrees 0 - 360°)
# pressure:     Air Pressure (HectoPascal hPA)
# rain:         Rain millimeters per h (mm/h)


WINDFINDER_URI = windFinder["WINDFINDER_URI"]

def windfinderString(Anemometer,  WindVane):
    WINDFINDER_ID = windFinder['WINDFINDER_ID']    
    WINDFINDER_PASS = windFinder["WINDFINDER_PASS"]
    date=datetime.now().strftime('%d.%m.%Y')
    time=datetime.now().strftime('%H:%M:%S')
    temperatureC, temperatureF, pressureHpa, pressureInch, humidity, psea  = bme280.readBME280All()
    try:
        params = urllib.urlencode({
                                    'sender_id':WINDFINDER_ID,
                                    'password':WINDFINDER_PASS,
                                    'date':date,
                                    'time':time,
                                    'windspeed':Anemometer.windKnots_10minAvg,
                                    'gust':Anemometer.gustKnots_10minutesAvg,
                                    'winddir':WindVane.averageWindDirection,
                                    'pressure':pressureHpa,
                                    'airtemp':temperatureC,
                                    })
        logger.debug(params)
    except Exception as e:
        print e
        logger.error(e)
    return params

        
        
# ************************
#         WINDGURU
# ************************

# uid 	(required) 	UID of your station = unique string you choosed during station registration
# interval        measurement interval in seconds (60 would mean you are sending 1 minute measurements), then the wind_avg / wind_max / wind_min values should be values valid for this past interval
# wind_avg        average wind speed during interval (knots)
# wind_max        maximum wind speed during interval (knots)
# wind_min        maximum wind speed during interval (knots)
# wind_direction  wind direction as degrees (0 = north, 90 east etc...)
# temperature     temperature (celsius)
# rh              relative humidity (%)
# mslp            pressure reduced to sea level (hPa)
# precip          precipitation in milimeters (not displayed anywhere yet, but API is ready to accept)
# precip_interval interval for the precip value in seconds (if not set then 3600 = 1 hour is assumed)
#
# Send only the measurement variables that you really have, skip those you don't have



WINDGURU_URI = windGuru["WINDGURU_URI"]

def windguruString(Anemometer,  WindVane):
    WINDGURU_STATION_ID = windGuru["WINDGURU_STATION_ID"]
    WINDGURU_API_PASSWORD = windGuru["WINDGURU_API_PASSWORD"]
    WINDGURU_SPOT_NAME = windGuru["WINDGURU_SPOT_NAME"]
    INTERVAL = windGuru["INTERVAL"]
    # hash (required) MD5 hash of a string that consists of 
    # salt, uid and station password concatenated together (in this order, see example below)
    # Authorization variables are required to validate your upload, example:
    
    # salt: 20180214171400
    # uid: stationXY (login password or the special API password, any of these will work)
    # station password: supersecret
    
    # then the hash would be calculated as md5("20180214171400stationXYsupersecret") = c9441d30280f4f6f4946fe2b2d360df5
    # Upload request example:
    # http://www.windguru.cz/upload/api.php?uid=stationXY&salt=20180214171400&hash=c9441d30280f4f6f4946fe2b2d360df5&wind_avg=12.5&wind_dir=165&temperature=20.5
    
    wgSalt= datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    wgHash=hashlib.md5("%s%s%s"%(wgSalt, WINDGURU_STATION_ID, WINDGURU_API_PASSWORD)).hexdigest()
    temperatureC, temperatureF, pressureHpa, pressureInch, humidity, psea  = bme280.readBME280All()
    try:
        params = urllib.urlencode({
                                    'uid':WINDGURU_STATION_ID,                                        
                                    'salt':wgSalt,                                        
                                    'hash':wgHash,                                        
                                    'interval':INTERVAL,            
                                    'wind_avg':Anemometer.windKnots_10minAvg,
                                    'windgustmph':Anemometer.gustKnots_10minutesAvg,
                                    'wind_direction':WindVane.averageWindDirection,
                                    'temperature':temperatureC,
                                    'rh':humidity,
                                    'mslp':pressureHpa,                                         
                                    })
        logger.debug(params)
    except Exception as e:
        print e
        logger.error(e)
    return params


# ********************************
# WEATHER UNDERGROUND 
# ********************************

# ********************************
# http://wiki.wunderground.com/index.php/PWS_-_Upload_Protocol
# ********************************

# NOT all fields need to be set, the _required_ elements are:
#    action
#    ID
#    PASSWORD
#    dateutc 

# action [action=updateraw] -- always supply this parameter to indicate you are making a weather observation upload
# ID [ID as registered by wunderground.com]
# PASSWORD [Station Key registered with this PWS ID, case sensitive]
# dateutc - [YYYY-MM-DD HH:MM:SS (mysql format)] In Universal Coordinated Time (UTC) Not local time

# winddir - [0-360 instantaneous wind direction]
# windspeedmph - [mph instantaneous wind speed]

# windgustmph - [mph current wind gust, using software specific time period]
# windgustdir - [0-360 using software specific time period]

# windspdmph_avg2m  - [mph 2 minute average wind speed mph]
# winddir_avg2m - [0-360 2 minute average wind direction]

# windgustmph_10m - [mph past 10 minutes wind gust mph ]
# windgustdir_10m - [0-360 past 10 minutes wind gust direction]

# humidity - [% outdoor humidity 0-100%]
# tempf - [F outdoor temperature] 
# baromin - [barometric pressure inches]

WEATHERUNDERGROUND_URI = wUnderground["WEATHERUNDERGROUND_URI"]

def weatherUndergroundString(Anemometer,  WindVane):
    # Station ID
    WEATHERUNDERGROUND_ID = wUnderground["WEATHERUNDERGROUND_ID"]
    # Station Key/Password
    WEATHERUNDERGROUND_KEY = wUnderground["WEATHERUNDERGROUND_KEY"]
    timestamp= datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")    
    temperatureC, temperatureF, pressureHpa, pressureInch, humidity, psea  = bme280.readBME280All()
    try:
        params = urllib.urlencode({
                                    'action':'updateraw',
                                    'ID':WEATHERUNDERGROUND_ID,
                                    'PASSWORD':WEATHERUNDERGROUND_KEY,                                        
                                    'winddir':WindVane.instantaneousWindDirection,            
                                    'windspeedmph':Anemometer.instaneousWindMilesPerHour,
                                    'windgustmph':Anemometer.gustMilesPerHour_10minutesAvg,
                                    'tempf':temperatureF,
                                    'humidity':humidity,
                                    'baromin':pressureInch, 
                                    'dateutc':timestamp, 
                                    'softwaretype':'raspberry_meteo'
                                    })
        logger.debug(params)
    except Exception as e:
        print e
        logger.error(e)
    return params


def updateWeather(uri, params):
    try:
        params = "?%s" % params            
        print params
        result = urllib.urlopen(uri + params)        
        feedback = result.read().strip()
        print "FEEDBACK***************"
        # windFinder returns html feedback
        if "<body>\nOK\n</body>" in feedback:
            feedback = "OK"
        print feedback
        logger.info(feedback)
    except Exception as e:
        print e
        logger.error("IO Error: %s", e.strerror)

if __name__ == "__main__":
    import weather
    an=weather.Anemometer()
    vane=weather.WindVane()
    time.sleep(2)
    while 1:        
        params = weatherUndergroundString(an, vane)
        updateWeather(WEATHERUNDERGROUND_URI, params)
        params = windguruString(an, vane)
        updateWeather(WINDGURU_URI, params)
        params = windfinderString(an, vane)
        updateWeather(WINDFINDER_URI, params)
        time.sleep(60*5)


     
        


