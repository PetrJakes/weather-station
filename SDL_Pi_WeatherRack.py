#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  SDL_Pi_WeatherRack.py - Raspberry Pi Python Library for SwitchDoc Labs WeatherRack.
#
#  SparkFun Weather Station Meters
#  Argent Data Systems
#  Created by SwitchDoc Labs February 13, 2015
#  Released into the public domain.
#    Version 1.3 - remove 300ms Bounce
#    Version 2.0 - Update for WeatherPiArduino V2
#    Version 3.0 - Removed Double Interrupts
#

# imports

try:
    # Check for user imports
    try:
        import conflocal as config
    except ImportError:
        import config
except:
    import NoWPAConfig.py as config
    
"""
# config contains
# device present global variables

AS3935_Present = False
DS3231_Present = False
BMP280_Present = False
FRAM_Present = False
HTU21DF_Present = False
AM2315_Present = False
ADS1015_Present = False
ADS1115_Present = False
"""

import sys
import time as time_
import math

from SDL_Adafruit_ADS1x15 import ADS1x15
import RPi.GPIO as GPIO

#GPIO.setwarnings(False)

from datetime import *

# constants
SDL_MODE_INTERNAL_AD = 0x00
SDL_MODE_I2C_ADS1015 = 0x01

# sample mode means return immediately.  THe wind speed is averaged at samplingInterval or when you ask, whichever is longer
SDL_MODE_SAMPLE = 0

# Delay mode means to wait for samplingInterval and the average after that time.
SDL_MODE_DELAY = 1

# Number of Interupts per Rain Bucket and Anemometer Clicks
SDL_INTERRUPT_CLICKS = 1
SDL_RAIN_BUCKET_CLICKS = 2

WIND_FACTOR = 2.400 / SDL_INTERRUPT_CLICKS

def AveragingWindDirections(listOfAngles):
    sinSum = 0
    cosSum = 0
    for angle in listOfAngles:
        sinSum += math.sin(math.radians(angle))
        cosSum += math.cos(math.radians(angle))
    return ((math.degrees(mat.atan2(sinSum, cosSum)) + 360) % 360)

def voltageToDegrees(voltage, lastKnownDirection):    

    if voltage >= 3.63433 and voltage < 3.93894:
        return 0.0
    if voltage >= 1.6925 and voltage < 2.11744:
        return 22.5
    if voltage >= 2.11744 and voltage < 2.58979:
        return 45
    if voltage >= 0.36541 and voltage < 0.43186:        
        return 67.5
    if voltage >= 0.43186 and voltage < 0.53555:
        return 90.0
    if voltage >= 0.2108 and voltage < 0.3654:
        return 112.5
    if voltage >= 0.7591 and voltage < 1.04761:
        return 135.0
    if voltage >= 0.53555 and voltage < 0.7591:
        return 157.5
    if voltage >= 1.29823 and voltage < 1.6925:
        return 180
    if voltage >= 1.04761 and voltage < 1.29823:
        return 202.5
    if voltage >= 3.00188 and voltage < 3.25418:
        return 225
    if voltage >= 2.58979 and voltage < 3.00188:
        return 247.5
    if voltage >= 4.47391 and voltage < 4.80769:
        return 270.0
    if voltage >= 3.93894 and voltage < 4.18656:
        return 292.5
    if voltage >= 4.18656 and voltage < 4.47391:
        return 315.0
    if voltage >= 3.25418 and voltage < 3.63433:
        return 337.5    
    return lastKnownDirection  # return previous voltage if not found

def recentTimeInMicros():
    # return current Time In Microseconds
    currentTimeInMicroseconds = int(round(time_.time() * 1000000))    
    return currentTimeInMicroseconds

def calculateMedian(list):
    data = sorted(list)
    n = len(data)
    if n == 0:
        return None
    if n % 2 == 1:
        return data[n // 2]
    else:
        i = n // 2
        return (data[i - 1] + data[i]) / 2

class SDL_Pi_WeatherRack:
    GPIO.setmode(GPIO.BCM)
#    GPIO.setwarnings(False)

    # instance variables
    _pinAnem = 0x00
    _pinRain = 0x00
    _intAnem = 0x00
    _intRain = 0x00
    _ADChannel = 0x00
    _ADMode = 0x00

    _currentRainCount = 0
    _currentRainMin = 0
    _lastRainTime = 0
    
    _windSwitchPulses = 0
    _currentWindSpeed = 0
    _currentWindDirection = 0
    _lastWindPulseTime = 0
    _shortestWindSwitchPulse = 0

    _samplingInterval = 5.0
    _windReadingMode = SDL_MODE_SAMPLE
    _samplingStartTime = 0

    _ads1015 =0

    def __init__(self, pinAnem, pinRain, intAnem, intRain, ADMode, adcContinuousConversion=0):
        self.adcContinuousConversion=adcContinuousConversion
        GPIO.setup(pinAnem, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(pinRain, GPIO.IN)        

        # when a rising edge is detected on port pinAnem or pinRain, regardless of whatever
        # else is happening in the program, the function callback will be run
        
        GPIO.add_event_detect(pinAnem, GPIO.RISING, callback=self.serviceInterruptAnem) 
        GPIO.add_event_detect(pinRain, GPIO.RISING, callback=self.serviceInterruptRain)
        ADS1015 = 0x00  # 12-bit ADC
        ADS1115 = 0x01  # 16-bit ADC

        # Select the gain
        self.gain = 6144  # +/- 6.144V
        # self.gain = 4096  # +/- 4.096V

        # Select the sample rate
        self.sps = 250  # 250 samples per second

        # Initialise the ADC using the default mode (use default I2C address)
        # Set this to ADS1015 or ADS1115 depending on the ADC you are using!
        self.ads1015 = ADS1x15(ic=ADS1015, address=0x48)

        # determine if device present
        try:
            value = self.ads1015.readRaw(0x01, self.gain, self.sps)  # AIN1 wired to wind vane on WeatherPiArduino
            time_.sleep(1.0)
            value = self.ads1015.readRaw(0x01, self.gain, self.sps)  # AIN1 wired to wind vane on WeatherPiArduino

            # now figure out if it is an ADS1015 or ADS1115
            if 0x0F & value == 0x00:
                config.ADS1015_Present = True
                config.ADS1115_Present = False

                # check again (1 out 16 chance of zero)
                value = self.ads1015.readRaw(0x00, self.gain, self.sps)  # AIN1 wired to wind vane on WeatherPiArduino
                if 0x0F & value == 0x00:
                    config.ADS1015_Present = True
                    config.ADS1115_Present = False
                else:

                    config.ADS1015_Present = False
                    config.ADS1115_Present = True
                    self.ads1015 = ADS1x15(ic=ADS1115, address=0x48)
            else:
                config.ADS1015_Present = False
                config.ADS1115_Present = True
                self.ads1015 = ADS1x15(ic=ADS1115, address=0x48)
        except TypeError as e:    
            print ('Type Error')
            config.ADS1015_Present = False
            config.ADS1115_Present = False

        SDL_Pi_WeatherRack._ADMode = ADMode

    # Wind Direction Routines
    def current_wind_direction(self):
        voltage, vaneVoltage, vcc= self.current_wind_direction_voltage()
        direction = voltageToDegrees(voltage, SDL_Pi_WeatherRack._currentWindDirection)
#        print "%0.4f ,%0.4f ,%0.4f, %3.2f" % (vcc,  vaneVoltage,  voltage,  direction)
        SDL_Pi_WeatherRack._currentWindDirection=direction
        return direction

    def current_wind_direction_voltage(self):
        # for some positions the wind vane returns very small voltage diferences 
        # 112.5° => 0.321V voltage difference 0.088V comparing to voltage for 67.5°
        #  67.5° => 0.409V voltage difference 0.045V comparing to voltage for 90.0°
        #  90.0° => 0.455V
        # because of that, we have to measure precisely as possible
        # to achive this goal it is necessary to measure Vcc voltage on the AIN0 pin (referential voltage) 
        # and using this value recalculate voltage measured on the voltage divider (wind vane) AIN1 pin        
        if SDL_Pi_WeatherRack._ADMode == SDL_MODE_I2C_ADS1015:
            # multiple readings  will supperes wind vane turbulent unstability moves
            if self.adcContinuousConversion:
                self.ads1015.startContinuousConversion(channel=1, sps=128) # data rate (samples per second)
                vaneVoltage = []
                for i in range(20):
                    vaneVoltage.append(self.ads1015.getLastConversionResults())
                    time_.sleep(0.02)                
                vaneVoltage=calculateMedian(vaneVoltage)    
                self.ads1015.startContinuousConversion(channel=0, sps=128) # data rate (samples per second)
                vcc = []
                for i in range(5):
                    vcc.append(self.ads1015.getLastConversionResults())
                    time_.sleep(0.02)                
                vcc=calculateMedian(vcc)    
            else:
                # first reading returns wrong value sometimes, lets read it twice
                self.ads1015.readADCSingleEnded(chanel=1, pga=self.gain, sps=self.sps) 
                vaneVoltage = self.ads1015.readADCSingleEnded(0x01, self.gain, self.sps)  # AIN1 wired to wind vane voltage divider
            # first reading returns wrong value sometimes, lets read it twice
            self.ads1015.readADCSingleEnded(0x00, self.gain, self.sps)  # AIN0 wired to Vcc - referential voltage
            vcc = self.ads1015.readADCSingleEnded(0x00, self.gain, self.sps)  # AIN0 wired to Vcc - referential voltage
            
            
        else:
            # user internal A/D converter
            voltage = 0.0
        # all voltages constants in the voltageToDegrees function are valid for 5V Vcc
        # lets recalculate value measured on the voltage divider to the value expected for 5V
        voltage = (vaneVoltage * (5000/vcc))
        
        return voltage/1000, vaneVoltage/1000, vcc/1000

    # Utility methods
    def setWindReadingMode(self, windReadingMode, samplingInterval):  
        SDL_Pi_WeatherRack._windReadingMode = windReadingMode
        SDL_Pi_WeatherRack._samplingInterval = samplingInterval  # sampling interval in seconds      
        if SDL_Pi_WeatherRack._windReadingMode == SDL_MODE_SAMPLE:
            SDL_Pi_WeatherRack._samplingStartTime = recentTimeInMicros()        

    def get_current_wind_speed_when_sampling(self):
        samplingIntervalInMicros = SDL_Pi_WeatherRack._samplingInterval * 1000000
        samplingInterval = recentTimeInMicros() - SDL_Pi_WeatherRack._samplingStartTime
        if samplingInterval >= samplingIntervalInMicros:
            # samp1ling time exceeded, calculate currentWindSpeed            
            SDL_Pi_WeatherRack._currentWindSpeed = float(SDL_Pi_WeatherRack._windSwitchPulses) / float(samplingInterval) * WIND_FACTOR * 1000000.0
            print "WindSpeed = %f, shortestPulse = %i, PulseCount=%i Pulses=%f" % (SDL_Pi_WeatherRack._currentWindSpeed, 
                                                                                                   SDL_Pi_WeatherRack._shortestWindSwitchPulse, 
                                                                                                   SDL_Pi_WeatherRack._windSwitchPulses, 
                                                                                                   float(SDL_Pi_WeatherRack._windSwitchPulses)/float(SDL_Pi_WeatherRack._samplingInterval)
                                                                                                   )
            SDL_Pi_WeatherRack._windSwitchPulses = 0
            SDL_Pi_WeatherRack._samplingStartTime = recentTimeInMicros()
        else:
            return SDL_Pi_WeatherRack._currentWindSpeed
         
        
    def current_wind_speed(self):  # in milliseconds
        if SDL_Pi_WeatherRack._windReadingMode == SDL_MODE_SAMPLE:
            self.get_current_wind_speed_when_sampling()
        else:
            # km/h * 1000 msec
            SDL_Pi_WeatherRack._windSwitchPulses = 0
            time_.sleep(SDL_Pi_WeatherRack._samplingInterval)
            SDL_Pi_WeatherRack._currentWindSpeed = float(SDL_Pi_WeatherRack._windSwitchPulses) / float(SDL_Pi_WeatherRack._samplingInterval) * WIND_FACTOR
        return SDL_Pi_WeatherRack._currentWindSpeed

    def get_wind_gust(self):
        shortestWindSwitchPulse = SDL_Pi_WeatherRack._shortestWindSwitchPulse
        SDL_Pi_WeatherRack._shortestWindSwitchPulse = 0xffffffff
        shortestWindSwitchPulse /= 1000000.0  # in seconds
        try:
            return 1.0 / float(shortestWindSwitchPulse) * WIND_FACTOR
        except ZeroDivisionError:
            return 0
        
    def reset_rain_total(self):
        SDL_Pi_WeatherRack._currentRainCount = 0
        
    def get_current_rain_total(self):
        rain_amount = 0.2794  * float(SDL_Pi_WeatherRack._currentRainCount) / SDL_RAIN_BUCKET_CLICKS
        SDL_Pi_WeatherRack._currentRainCount = 0x00
        return rain_amount


    # Interrupt Routines
    def serviceInterruptAnem(self, channel):
        # print "Anem Interrupt Service Routine"
        recTimeInMicros = recentTimeInMicros()
        samplingInterval = recTimeInMicros - SDL_Pi_WeatherRack._lastWindPulseTime
        SDL_Pi_WeatherRack._lastWindPulseTime = recTimeInMicros
        SDL_Pi_WeatherRack._windSwitchPulses += 1
        if samplingInterval < SDL_Pi_WeatherRack._shortestWindSwitchPulse:
            SDL_Pi_WeatherRack._shortestWindSwitchPulse = samplingInterval

    def serviceInterruptRain(self, channel):
#        print 'Rain Interrupt Service Routine'
        recTimeInMicros = recentTimeInMicros()
        timeDelta = recTimeInMicros - SDL_Pi_WeatherRack._lastRainTime
        SDL_Pi_WeatherRack._lastRainTime = recTimeInMicros
        if timeDelta > 500:  # debounce
            SDL_Pi_WeatherRack._currentRainCount += 1
            if timeDelta < SDL_Pi_WeatherRack._currentRainMin:
                SDL_Pi_WeatherRack._currentRainMin = timeDelta

    def returnInterruptClicks(self):
        return SDL_INTERRUPT_CLICKS




