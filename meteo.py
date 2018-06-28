#!/usr/bin/python

"""
sending weather data from 
to:
- wunderground
- windguru
"""

import subprocess
import time
import urllib
import datetime
import logging
import logging.handlers as handlers
import ConfigParser
from datetime import datetime
import hashlib


LOG_FILENAME='/var/log/weatherd.log'
FORMAT = "%(asctime)s %(levelname)s %(message)s "

logger = logging.getLogger("weatherd")
logger.setLevel(logging.INFO)
handler = handlers.RotatingFileHandler(LOG_FILENAME, mode='a', maxBytes=10000, backupCount=3)
formatter = logging.Formatter(FORMAT, "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

# WINDGURU
"""
uid 	(required) 	UID of your station = unique string you choosed during station registration
interval        measurement interval in seconds (60 would mean you are sending 1 minute measurements), then the wind_avg / wind_max / wind_min values should be values valid for this past interval
wind_avg        average wind speed during interval (knots)
wind_max        maximum wind speed during interval (knots)
wind_min        maximum wind speed during interval (knots)
wind_direction  wind direction as degrees (0 = north, 90 east etc...)
temperature     temperature (celsius)
rh              relative humidity (%)
mslp            pressure reduced to sea level (hPa)
precip          precipitation in milimeters (not displayed anywhere yet, but API is ready to accept)
precip_interval interval for the precip value in seconds (if not set then 3600 = 1 hour is assumed)

Send only the measurement variables that you really have, skip those you don't have
"""
WG_URI = "http://www.windguru.cz/upload/api.php"
WG_STATION_ID = "foersterova449"
WG_API_PASSWORD = "atapol**7"
WG_SPOT_NAME = "Foersterova 449"
wgSalt = "has to refresh before upload"

def wgString(ID=WG_STATION_ID, KEY=WG_API_PASSWORD, windDeg=0, windSpeed=10,  windGust=15, temp=24, hum=45, pressure=1000 ):
    wgSalt= datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    # hash (required) MD5 hash of a string that consists of 
    # salt, uid and station password concatenated together (in this order, see example below)
    # Authorization variables are required to validate your upload, example:
    
    # salt: 20180214171400
    # uid: stationXY (login password or the special API password, any of these will work)
    # station password: supersecret
    
    # then the hash would be calculated as md5("20180214171400stationXYsupersecret") = c9441d30280f4f6f4946fe2b2d360df5     
    wgHash=hashlib.md5("%s%s%s"%(wgSalt,WG_STATION_ID,WG_API_PASSWORD)).hexdigest()
    try:
        params = urllib.urlencode({
                                        'uid':ID,                                        
                                        'salt':wgSalt,                                        
                                        'hash':wgHash,                                        
                                        'interval':60,            
                                        'wind_avg':windSpeed,
                                        'windgustmph':windGust,
                                        'wind_direction':windDeg, 
                                        'wind_direction':windDeg, 
                                        'temperature':temp,
                                        'rh':hum,
                                        'mslp':pressure,                                         
                                        })
        logger.debug(params)
    except ConfigParser.NoSectionError:
        logger.error("Missing config section")
    except Exception as e:
        print e
        logger.error(e)
    return params

# Upload request example:
# http://www.windguru.cz/upload/api.php?uid=stationXY&salt=20180214171400&hash=c9441d30280f4f6f4946fe2b2d360df5&wind_avg=12.5&wind_dir=165&temperature=20.5


# ********************************
# WEATHER UNDERGROUND
# Station ID
ID = "IJIN41"
# Station Key/Password
KEY = "17kzwbjg"

wu_uri = 'http://rtupdate.wunderground.com/weatherstation/updateweatherstation.php'

def wuString(ID=ID, KEY=KEY, windDeg=0, windSpeed=10,  windGust=15, temp=24, hum=45 ):
    timestamp= datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")    
    try:
        params = urllib.urlencode({
                                        'action':'updateraw',
                                        'ID':ID,
                                        'PASSWORD':KEY,                                        
                                        'winddir':windDeg,            
                                        'windspeedmph':windSpeed,
                                        'windgustmph':windGust,
                                        'tempf':temp,
                                        'humidity':hum,
                                        'dateutc':timestamp, 
                                        'softwaretype':'raspberry_meteo'
                                        })
        logger.debug(params)
    except ConfigParser.NoSectionError:
        logger.error("Missing config section")
    except Exception as e:
        print e
        logger.error(e)
    return params


def updateWeather(uri, params):
    timestamp= datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
#        logger.info(params)
        print params
        params = "?%s" % params            
        print params
        result = urllib.urlopen(uri + params)        
        feedback = result.read().strip()
        print feedback
        logger.info(feedback)
    except IOError as e:
        print e
        logger.error("IO Error: %s", e.strerror)

if __name__ == "__main__":
#    params = wuString()
#    updateWeather(wu_uri, params)
    while 1:
        params = wgString()
        updateWeather(WG_URI, params)
        time.sleep(60)


     
        


