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

import sys
import time as time_

sys.path.append('../SDL_Adafruit_ADS1x15')

from SDL_Adafruit_ADS1x15 import ADS1x15
import RPi.GPIO as GPIO

GPIO.setwarnings(False)

from datetime import *

# constants
SDL_MODE_INTERNAL_AD = 0x00
SDL_MODE_I2C_ADS1015 = 0x01

# sample mode means return immediately.  THe wind speed is averaged at sampleTime or when you ask, whichever is longer
SDL_MODE_SAMPLE = 0x00

# Delay mode means to wait for sampleTime and the average after that time.
SDL_MODE_DELAY = 0x01

# Number of Interupts per Rain Bucket and Anemometer Clicks
SDL_INTERRUPT_CLICKS = 0x01
SDL_RAIN_BUCKET_CLICKS = 2

WIND_FACTOR = 2.400 / SDL_INTERRUPT_CLICKS



def voltageToDegrees(value, defaultWindDirection):    

#    ADJUST3OR5 = 1.0 # For Vcc 5V, use 1.0.  For Vcc 3.3V use 0.66 (3.3/5 = 0.66)

    if value >= 3.63433 and value < 3.93894:
        return 0.0

    if value >= 1.6925 and value < 2.11744:
        return 22.5

    if value >= 2.11744 and value < 2.58979:
        return 45

    if value >= 0.36541 and value < 0.43186:
        # high margin value incrased manualy after some testing
        # calculated voltage value = 0.43186        
        return 67.5

    if value >= 0.43186 and value < 0.53555:
        # low margine value decrased manualy after some testing
        # calculated voltage value = 0.43186
        return 90.0

    if value >= 0.2108 and value < 0.3654:
        return 112.5

    if value >= 0.7591 and value < 1.04761:
        return 135.0

    if value >= 0.53555 and value < 0.7591:
        return 157.5

    if value >= 1.29823 and value < 1.6925:
        return 180

    if value >= 1.04761 and value < 1.29823:
        return 202.5

    if value >= 3.00188 and value < 3.25418:
        return 225

    if value >= 2.58979 and value < 3.00188:
        return 247.5

    if value >= 4.47391 and value < 4.80769:
        return 270.0

    if value >= 3.93894 and value < 4.18656:
        return 292.5

    if value >= 4.18656 and value < 4.47391:
        return 315.0

    if value >= 3.25418 and value < 3.63433:
        return 337.5

    return defaultWindDirection  # return previous value if not found


# return current microseconds

def micros():
    microseconds = int(round(time_.time() * 1000000))
    return microseconds


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
    GPIO.setwarnings(False)

    # instance variables
    _currentWindCount = 0x00
    _currentRainCount = 0x00

    _pinAnem = 0x00
    _pinRain = 0x00
    _intAnem = 0x00
    _intRain = 0x00
    _ADChannel = 0x00
    _ADMode = 0x00

    _currentRainCount = 0x00
    _currentWindCount = 0x00
    _currentWindSpeed = 0.0
    _currentWindDirection = 0.0

    _lastWindTime = 0x00
    _shortestWindTime = 0x00

    _sampleTime = 5.0
    _selectedMode = SDL_MODE_SAMPLE
    _startSampleTime = 0x00

    _currentRainMin = 0x00
    _lastRainTime = 0x00

    _ads1015 = 0x00

    def __init__(self, pinAnem, pinRain, intAnem, intRain, ADMode, adcContinuousConversion=0):
        self.adcContinuousConversion=adcContinuousConversion
        GPIO.setup(pinAnem, GPIO.IN)
        GPIO.setup(pinRain, GPIO.IN)
        # when a falling edge is detected on port pinAnem, regardless of whatever
        # else is happening in the program, the function callback will be run

        # GPIO.add_event_detect(pinAnem, GPIO.RISING, callback=self.serviceInterruptAnem)
        # GPIO.add_event_detect(pinRain, GPIO.RISING, callback=self.serviceInterruptRain)

        GPIO.add_event_detect(pinAnem, GPIO.RISING, callback=self.serviceInterruptAnem,bouncetime=40)
        GPIO.add_event_detect(pinRain, GPIO.RISING, callback=self.serviceInterruptRain,bouncetime=40)
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
        voltage= self.current_wind_direction_voltage()
        direction = voltageToDegrees(voltage, SDL_Pi_WeatherRack._currentWindDirection)
        return direction

    def current_wind_direction_voltage(self):
        # for some positions the wind vane returns very small voltage diferences 
        # 112.5° => 0.321V voltage difference 0.088V comparing with voltage for 67.5°
        #  67.5° => 0.409V voltage difference 0.045V comparing with voltage for 90.0°
        #  90.0° => 0.455V
        # so we have to measure precisely as possible
        # to achive this goal we recalculate voltage measured on the voltage divider (wind vane) AIN1 pin
        # using referential Vcc voltage measured on AIN0 pin
        if SDL_Pi_WeatherRack._ADMode == SDL_MODE_I2C_ADS1015:
            if self.adcContinuousConversion:
                self.ads1015.startContinuousConversion(channel=0, sps=128) # data rate (samples per second)
                vcc=[]
                for i in range(10):
                    if i > 4:
                        vcc.append(self.ads1015.getLastConversionResults())
                    else:
                        self.ads1015.getLastConversionResults()
                    time_.sleep(0.01)
                vcc = calculateMedian(vcc)
                self.ads1015.startContinuousConversion(channel=1, sps=128) # data rate (samples per second)
                vaneVoltage = []
                for i in range(10):
                    if i > 4:
                        vaneVoltage.append(self.ads1015.getLastConversionResults())
                    else:
                        self.ads1015.getLastConversionResults()
                    time_.sleep(0.01)
                vaneVoltage=calculateMedian(vaneVoltage)
                
            else:
                vcc = self.ads1015.readADCSingleEnded(0x00, self.gain, self.sps)  # AIN0 wired to Vcc - referential voltage
                vaneVoltage = self.ads1015.readADCSingleEnded(0x01, self.gain, self.sps)  # AIN1 wired to wind vane voltage divider
            voltage = (vaneVoltage * 5000/(vcc))/1000  # 5000 = expected Vcc voltage
            print "vcc:", vcc/1000
            print "V read: ", vaneVoltage/1000
            print "V calc: ", voltage
            print "V diff: ", vaneVoltage/1000 - voltage
        else:
            # user internal A/D converter
            voltage = 0.0
        return voltage

    # Utility methods
    def reset_rain_total(self):
        SDL_Pi_WeatherRack._currentRainCount = 0x00

    def accessInternalCurrentWindDirection(self):
        return SDL_Pi_WeatherRack._currentWindDirection

    def reset_wind_gust(self):
        SDL_Pi_WeatherRack._shortestWindTime = 0xffffffff

    def startWindSample(self, sampleTime):
        SDL_Pi_WeatherRack._startSampleTime = micros()
        SDL_Pi_WeatherRack._sampleTime = sampleTime

    def get_current_wind_speed_when_sampling(self):
        compareValue = SDL_Pi_WeatherRack._sampleTime * 1000000
        if micros() - SDL_Pi_WeatherRack._startSampleTime >= compareValue:
            # sample time exceeded, calculate currentWindSpeed
            timeSpan = micros() - SDL_Pi_WeatherRack._startSampleTime
            SDL_Pi_WeatherRack._currentWindSpeed = float(SDL_Pi_WeatherRack._currentWindCount) / float(timeSpan) * WIND_FACTOR * 1000000.0
            # print "SDL_CWS = %f, SDL_Pi_WeatherRack._shortestWindTime = %i, CWCount=%i TPS=%f" % (SDL_Pi_WeatherRack._currentWindSpeed,SDL_Pi_WeatherRack._shortestWindTime, SDL_Pi_WeatherRack._currentWindCount, float(SDL_Pi_WeatherRack._currentWindCount)/float(SDL_Pi_WeatherRack._sampleTime))
            SDL_Pi_WeatherRack._currentWindCount = 0x00
            SDL_Pi_WeatherRack._startSampleTime = micros()
         # print "SDL_Pi_WeatherRack._currentWindSpeed=", SDL_Pi_WeatherRack._currentWindSpeed
        return SDL_Pi_WeatherRack._currentWindSpeed

    def setWindMode(self, selectedMode, sampleTime):  # time in seconds
        SDL_Pi_WeatherRack._sampleTime = sampleTime
        SDL_Pi_WeatherRack._selectedMode = selectedMode
        if SDL_Pi_WeatherRack._selectedMode == SDL_MODE_SAMPLE:
            self.startWindSample(SDL_Pi_WeatherRack._sampleTime)

    def get_current_rain_total(self):
        rain_amount = 0.2794  * float(SDL_Pi_WeatherRack._currentRainCount) / SDL_RAIN_BUCKET_CLICKS
        SDL_Pi_WeatherRack._currentRainCount = 0x00
        return rain_amount

    def current_wind_speed(self):  # in milliseconds
        if SDL_Pi_WeatherRack._selectedMode == SDL_MODE_SAMPLE:
            SDL_Pi_WeatherRack._currentWindSpeed = self.get_current_wind_speed_when_sampling()
        else:
            # km/h * 1000 msec
            SDL_Pi_WeatherRack._currentWindCount = 0x00
            delay(SDL_Pi_WeatherRack._sampleTime * 1000)
            SDL_Pi_WeatherRack._currentWindSpeed = float(SDL_Pi_WeatherRack._currentWindCount) / float(SDL_Pi_WeatherRack._sampleTime) * WIND_FACTOR
        return SDL_Pi_WeatherRack._currentWindSpeed

    def get_wind_gust(self):
        latestTime = SDL_Pi_WeatherRack._shortestWindTime
        SDL_Pi_WeatherRack._shortestWindTime = 0xffffffff
        time = latestTime / 1000000.0  # in microseconds
        if time == 0x00:
            return 0x00
        else:
            return 1.0 / float(time) * WIND_FACTOR

    # Interrupt Routines
    def serviceInterruptAnem(self, channel):
        # print "Anem Interrupt Service Routine"
        currentTime = micros() - SDL_Pi_WeatherRack._lastWindTime
        SDL_Pi_WeatherRack._lastWindTime = micros()
        if currentTime > 4000:  # debounce
            SDL_Pi_WeatherRack._currentWindCount = SDL_Pi_WeatherRack._currentWindCount + 0x01
            if currentTime < SDL_Pi_WeatherRack._shortestWindTime:
                SDL_Pi_WeatherRack._shortestWindTime = currentTime
        else:
            print 'currentTime=%i' % currentTime
            print 'DEBOUNCE-count=%i' % SDL_Pi_WeatherRack._currentWindCount

    def serviceInterruptRain(self, channel):
        print 'Rain Interrupt Service Routine'
        currentTime = micros() - SDL_Pi_WeatherRack._lastRainTime
        SDL_Pi_WeatherRack._lastRainTime = micros()
        if currentTime > 500:  # debounce
            SDL_Pi_WeatherRack._currentRainCount = SDL_Pi_WeatherRack._currentRainCount + 0x01
            if currentTime < SDL_Pi_WeatherRack._currentRainMin:
                SDL_Pi_WeatherRack._currentRainMin = currentTime

    def returnInterruptClicks(self):
        return SDL_INTERRUPT_CLICKS




