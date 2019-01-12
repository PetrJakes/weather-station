#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Partialy used code from 
#  SDL_Pi_WeatherRack.py - Raspberry Pi Python Library for SwitchDoc Labs WeatherRack.
#  SparkFun Weather Station Meters
#  Argent Data Systems
#  Created by SwitchDoc Labs February 13, 2015

from __future__ import division
import time
from SDL_Adafruit_ADS1x15 import ADS1x15
import math
from threading import Thread
import I2C_LCD_driver
import bme280
import datetime
import pigpio
import meteo

import configparser
config = configparser.ConfigParser()

config.read('weather.ini')

settings= config['SETTINGS']

LCD_ADDRESS=int(settings["LCD_ADDRESS"], 16)

class WindVane(object):
    """ Class for reading voltage from wind wane 
    
    WMO requirements for wind wane measurment (see below) will be fulfiled
    using function to calculate an "average (mean) of an angle" 
   
   ********* WMO requirements ***************************************    
    WMO GUIDE TO METEOROLOGICAL INSTRUMENTS AND METHODS OF OBSERVATION 
    https://library.wmo.int/opac/doc_num.php?explnum_id=3177
    https://library.wmo.int/pmb_ged/wmo_8_en-2012.pdf
    
    Wind direction should be reported in degrees to the nearest 10°, 
    using a 01 ... 36 code (for example, code 2 means that the wind direction
    is between 15 and 25°), and should represent an average over 10 min.
    Wind direction is defined as the direction from which the wind blows, and is
    measured clockwise from geographical north, namely, true north.  
    
    The wind direction is measured with a vane that has 7 bit digital encoder
    that is sampled every second. 
    Averages and standard deviations are computed over 10 min intervals, where
    successive samples are checked for continuity. If two successive samples 
    differ by more than 180°, the difference is decreased by adding or 
    subtracting 360° from the second sample.
    """
    def __init__(self):
        ADS1115 = int(settings["ADS1115"]) # 16-bit ADC
        
        ADS1115_ADDRESS = int(settings["ADS1115_ADDRESS"], 16)
        ADS1115_GAIN = float(settings["ADS1115_GAIN"])
        ADS1115_SPS = int(settings["ADS1115_SPS"])
        
        self.REFERENTIAL_VOLTAGE = float(settings["REFERENTIAL_VOLTAGE"])
        self.gain = int(ADS1115_GAIN)
        self.sps = int(ADS1115_SPS)

        # Select the sample rate
        self.sps = 250  # 250 samples per second

        # Initialise the ADC using the default mode (use default I2C address)
        # Set this to ADS1015 or ADS1115 depending on the ADC you are using!
        self.ads1115 = ADS1x15(ic=ADS1115, address=ADS1115_ADDRESS)        
        
        self.instaneousWindDirection=0
        self._windDirectionQueue=[]
        self._windDirectionHistoryInterval=60*10 # 10 minutes
        self.readWindDirection()
        
        # start wind reading thread
        self.th=Thread(target=self.startReadingWind)
        self.th.daemon = True
        self.th.start()
        
        
    def startReadingWind(self):
        try:
            while True:
                self.readWindDirection()
                time.sleep(1)
        except KeyboardInterrupt:            
            return
        
    def recentWindDirectionVoltage(self):
        # for some positions the wind vane returns very small voltage diferences 
        # 112.5° => 0.321V voltage difference 0.088V comparing to the voltage for 67.5°
        #  67.5° => 0.409V voltage difference 0.045V comparing to the voltage for 90.0°
        #  90.0° => 0.455V
        # 
        # voltages in voltageToDegrees method are calculated/measured with the referential voltage 5V
        # in the real condition, the Vcc voltage of the Raspberry Pi can vary
        # to measure wind wane voltage precisely, we measure Raspberry Pi Vcc voltage first - ADS1115 AIN0 pin
        # this is real referential voltage
        # using this value we recalculate voltage measured on the voltage divider (wind vane) AIN1 pin                
        
        
        # first reading returns wrong value sometimes, lets read it twice
        # AIN1 wired to wind vane voltage divider
        self.ads1115.readADCSingleEnded(channel=1, pga=self.gain, sps=self.sps)         
        vaneVoltage = self.ads1115.readADCSingleEnded(channel=1, pga=self.gain, sps=self.sps)  
                
        # first reading returns wrong value sometimes, lets read it twice
        # AIN0 wired to Vcc - referential voltage        
        self.ads1115.readADCSingleEnded(channel=0, pga=self.gain, sps=self.sps)
        vcc = self.ads1115.readADCSingleEnded(channel=0, pga=self.gain, sps=self.sps)
        calculatedVoltage = (vaneVoltage * (self.REFERENTIAL_VOLTAGE/vcc))
        return calculatedVoltage/1000, vaneVoltage/1000, vcc/1000
        
        
    def readWindDirection(self):
        calculatedVoltage, vaneVoltage, vcc= self.recentWindDirectionVoltage()
        self.instaneousWindDirection = self.voltageToDegrees(calculatedVoltage, self.instaneousWindDirection)
#        print "%0.4f ,%0.4f ,%0.4f, %3.2f" % (vcc,  vaneVoltage,  voltage,  self.instaneousWindDirection)        
        self.maintainWindDirectionQueue()
        return self.averageWindDirection
        
        
    def maintainWindDirectionQueue(self):
        self._windDirectionQueue.append(self.instaneousWindDirection)
        queueLenght = len(self._windDirectionQueue)        
        if queueLenght > self._windDirectionHistoryInterval:
            diff = queueLenght - self._windDirectionHistoryInterval
            del self._windDirectionQueue[:diff]            
        # Wind direction should be reported in degrees to the nearest 10°
        self.averageWindDirection = round(self.averageWindDirections(self._windDirectionQueue), -1)
        self.instantaneousWindDirection=self._windDirectionQueue[-1]
            
        
    def voltageToDegrees(self, voltage, lastKnownDirection):
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
        
    def averageWindDirections(self, listOfAngles):
        sinSum = 0
        cosSum = 0
        for angle in listOfAngles:
            sinSum += math.sin(math.radians(angle))
            cosSum += math.cos(math.radians(angle))
        return ((math.degrees(math.atan2(sinSum, cosSum)) + 360) % 360)        

class Anemometer(object):
    """Class for reading pulses from the cup rotating anemometer

    Wind speed is calculated using "Pulse Counting Method":
    Pulse counting method uses a sampling period (t) and the number of pulses (n) 
    that are counted over the sampling period. 
    Knowing the number of pulses per revolution (N) for the anemometer, the speed can be calculated.
    - 1Hz pwm pulses are generated on the output pin 
    - pwm signal is wired to the input pin
    - when a rising edge is detected on the input pin, regardless of whatever
      else is happening in the program, the function callback will be run
      to calculate pulses per second 
      
    ***********************************************************
    pulses are recorded according to the 
    WMO GUIDE TO METEOROLOGICAL INSTRUMENTS AND METHODS OF OBSERVATION 
    https://library.wmo.int/opac/doc_num.php?explnum_id=3177
    https://library.wmo.int/pmb_ged/wmo_8_en-2012.pdf
    Recommendations for the design of wind-measuring systems:
    
    The extreme has to be determined from 3 s averages, namely, by averaging
    over the last 12 samples. This averaging has to be done every 0.25 s 
    (namely, overlapping 3 s averages every 0.25 s).
    
    ... In order to determine peak gusts accurately, it is desirable 
    to sample the filtered wind signal every 0.25 s (frequency 4 Hz)...
    
    From recorded pulses, RPM is calculated and converted to the wind speed 
    (m/s, knots).    
    1 meter/second is equal to 1.9438444924406 knot.
    1 knot is equal to 0.51444444444444 m/s
    1 knot = 1 nautical mile/hour = 1.85200 kilometer/hour
    
    Wind speed should be reported to a resolution of 0.5 m/s or in knots 
    (0.515 m/s) to the nearest unit, and should represent, for synoptic reports,
    an average over 10 min.  
    * round(45.1*2)/2
    
    Calibration of the anemometer using GPS is well described here:
    http://www.yoctopuce.com/EN/article/how-to-measure-wind-part-1
    * google "libreoffice trendline to a chart equation"

    """    
          
    warning = """
            The GPIO for hardware_PWM must be one of the following:
            12  PWM channel 0  All models but A and B
            13  PWM channel 1  All models but A and B
            18  PWM channel 0  All models
            19  PWM channel 1  All models but A and B
            
            40  PWM channel 0  Compute module only
            41  PWM channel 1  Compute module only
            45  PWM channel 1  Compute module only
            52  PWM channel 0  Compute module only
            53  PWM channel 1  Compute module only
            """     
    
    def __init__(self):
        WIND_HISTORY_INTERVAL = int(settings["WIND_HISTORY_INTERVAL"])
        PULSES_PER_REVOLUTION = int(settings["PULSES_PER_REVOLUTION"])
        PIN_ANEMO_PULSES_INPUT = int(settings["PIN_ANEMO_PULSES_INPUT"])
        
        PIN_SAMPLING_PULSES_OUTPUT = int(settings["PIN_SAMPLING_PULSES_OUTPUT"])
        SAMPLING_FREQUENCY = int(settings["SAMPLING_FREQUENCY"])
        PIN_RPS_SAMPLER_INPUT = int(settings["PIN_RPS_SAMPLER_INPUT"])
        self.PULSES_TO_MPS_QUOTIENT = float(settings["PULSES_TO_MPS_QUOTIENT"])
        MIN_RPS = int(settings["MIN_RPS"])
        MAX_RPS = int(settings["MAX_RPS"])
        
        
        if PIN_SAMPLING_PULSES_OUTPUT!=18:
            print Anemometer.warning
        self.rpsQueue=[0]
        self.gustQueue=[0]
        self.WIND_HISTORY_INTERVAL=WIND_HISTORY_INTERVAL        
        self.PULSES_PER_REVOLUTION=float(PULSES_PER_REVOLUTION)                
        self.MIN_RPS=MIN_RPS
        self.MAX_RPS=MAX_RPS
        self.SAMPLING_FREQUENCY = SAMPLING_FREQUENCY                        
        self._lastPulsesCount=0
        self.gustInterval = 3*SAMPLING_FREQUENCY # intended to be 3 seconds
        self.windMetersPerSecond_10minAvg=0
        self.windKmph_10minutesAvg=0
        self.windKnots_10minAvg=0        
        self.windMilesPerHour_10minAvg=0        
        self.gust_metersPerSecond_10minutesAvg=0
        self.recentGustKmph=0
        self.recentGustKnots=0
        self.recentGustMilesPerHour=0
        
        pi=pigpio.pi()
        
        
        # anemometer pulses input
        # when a rising edge is detected on port PIN_ANEMO_PULSES_INPUT, regardless of whatever
        # else is happening in the program, the function callback will be run
        # If a user callback is not specified a default tally callback is provided which simply counts edges
        pi.set_mode(PIN_ANEMO_PULSES_INPUT, pigpio.INPUT)
        pi.set_pull_up_down(PIN_ANEMO_PULSES_INPUT, pigpio.PUD_DOWN)
        self.cb1=pi.callback(user_gpio=PIN_ANEMO_PULSES_INPUT, edge=pigpio.EITHER_EDGE)
        
        # sampling frequency generator input
        pi.set_mode(PIN_RPS_SAMPLER_INPUT, pigpio.INPUT)
        pi.set_pull_up_down(PIN_RPS_SAMPLER_INPUT, pigpio.PUD_DOWN)
        pi.callback(user_gpio=PIN_RPS_SAMPLER_INPUT, edge=pigpio.RISING_EDGE, func=self._windCalculator)
        
        # sampling frequency generator output
        pi.hardware_PWM(PIN_SAMPLING_PULSES_OUTPUT, SAMPLING_FREQUENCY, 500000)# start PWM pulses: Broadcom pin 18, 50% dutycycle 

    def _windCalculator(self, gpio, level, tick):
        # every time sampling signal occures, average RPS is calculated
        # and appended to the RPS Queue
        # than wind mean speed and gust is calculated 
        self._maintainPulsesCounter()
        self._appendRpsQueue()
        self._apendGustQueue()
        self._maintainQueues()        
        self._meanWindRps()
        self._gustWindRps()
        self._calculateWind()

    def _maintainPulsesCounter(self):
        pulsesSinceStart = self.cb1.tally()        
        self._pulsesCount = pulsesSinceStart-self._lastPulsesCount
        self._lastPulsesCount = pulsesSinceStart
        
    def _appendRpsQueue(self):
        # calculate number of pulses per second
        pulsesPerSecond = self._pulsesCount * self.SAMPLING_FREQUENCY
        rps = pulsesPerSecond / self.PULSES_PER_REVOLUTION        
        self.rpsQueue.append(rps)

    def _apendGustQueue(self):
        try:
            # calculate last known gust 
            recentAverageGustRps = sum(self.rpsQueue[-self.gustInterval:])/self.gustInterval            
        except IndexError as e:
            recentAverageGustRps = sum(self.rpsQueue)/len(self.rpsQueue)
        self.gustQueue.append(recentAverageGustRps)

    def _maintainQueues(self):
        queueLenght = len(self.rpsQueue)
        windHistoryInterval=self.WIND_HISTORY_INTERVAL*self.SAMPLING_FREQUENCY 
        if queueLenght > windHistoryInterval:
            diff = queueLenght - windHistoryInterval
            del self.rpsQueue[:diff]
            del self.gustQueue[:diff]

    def _meanWindRps(self):
        last2Minutes = 2*60*self.SAMPLING_FREQUENCY        
        try:
            rps_2minutesAvg = sum(self.rpsQueue[-last2Minutes:]) / last2Minutes
            rps_10minutesAvg = sum(self.rpsQueue) / len(self.rpsQueue)            
            self.windRps_10minutesAvg = rps_10minutesAvg
            self.windRps_2minutesAvg = rps_2minutesAvg
        except ZeroDivisionError as e:            
            self.windRps_10minutesAvg = 0
            self.windRps_2minutesAvg = 0
    
    def _gustWindRps(self):
        self.windGustRps_10min=max(self.gustQueue)
        last2Minutes = 2*60*self.SAMPLING_FREQUENCY
        self.windGustRps_2min = max(self.gustQueue[-last2Minutes:])
        
    def _calculateWind(self):
        # Wind speed should be reported to a resolution of 0.5 m/s
        
        # wind speed
        windMetersPerSecond_10minAvg = self._round(self.windRps_10minutesAvg * self.PULSES_TO_MPS_QUOTIENT)
        instaneousWindMetersPerSecond = self._round(self.rpsQueue[-1] * self.PULSES_TO_MPS_QUOTIENT)
        
        self.windMetersPerSecond_10minAvg = windMetersPerSecond_10minAvg
        self.windKmph_10minutesAvg = self._round(windMetersPerSecond_10minAvg * 3.6)
        self.windKnots_10minAvg = self._round(windMetersPerSecond_10minAvg * 1.9438444924574)
        self.windMilesPerHour_10minAvg=self._round(windMetersPerSecond_10minAvg * 2.2369362920544)
        
        self.instaneousWindMetersPerSecond = instaneousWindMetersPerSecond
        self.instaneousWindMilesPerHour = self._round(instaneousWindMetersPerSecond* 2.2369362920544)
        
        # gust
        gust_metersPerSecond_2minutesAvg = self._round(self.windGustRps_2min * self.PULSES_TO_MPS_QUOTIENT)
        gust_metersPerSecond_10minutesAvg = self._round(self.windGustRps_10min * self.PULSES_TO_MPS_QUOTIENT)
        self.gust_metersPerSecond_10minutesAvg=gust_metersPerSecond_10minutesAvg
        self.gustKmph_10minutesAvg = self._round(gust_metersPerSecond_10minutesAvg * 3.6)
        self.gustKnots_10minutesAvg = self._round(gust_metersPerSecond_10minutesAvg * 1.9438444924574)
        self.gustMilesPerHour_2minutesAvg=self._round(gust_metersPerSecond_2minutesAvg * 2.2369362920544)
        self.gustMilesPerHour_10minutesAvg=self._round(gust_metersPerSecond_10minutesAvg * 2.2369362920544)
#TODO:
# windgustmph - [mph current wind gust, using software specific time period]
# windgustdir - [0-360 using software specific time period]        
        
        
    def _round(self, nmber):
        # rounding to xx.5
        return round(nmber*2)/2
        
        
def birthday():
    # Easter Egg to display Happy Brithday for your friends on the LCD display
    birthdayDict={                      
                      "February-9":"Jang Jungyong", 
                      "February-12":"Mek", 
                      "February-13":"Sabu",
                      "April-11":"Domin", 
                      "May-24": "Jeff",                      
                      "June-3":"Kim Heon-Su",
                      "June-10":"Son",
                      "October-1":"Petr"
                      }
    d = datetime.date.today()
    try:
        return birthdayDict[d.strftime('%B-%d')]
    except KeyError:
        pass

    
def main():
    an=Anemometer()
    vane=WindVane()
    time.sleep(2) # wait till first wind is measured
    dispayConnected=True
    try:
        mylcd = I2C_LCD_driver.lcd(ADDRESS=LCD_ADDRESS)
    except IOError as e:
        dispayConnected=False
    
    print "===================================="
    try:
        while True:
#TODO: sending to the web pages
            params = meteo.weatherUndergroundString(an, vane)
            meteo.updateWeather(meteo.WEATHERUNDERGROUND_URI, params)
            params = meteo.windguruString(an, vane)
            meteo.updateWeather(meteo.WINDGURU_URI, params)
            params = meteo.windfinderString(an, vane)
            meteo.updateWeather(meteo.WINDFINDER_URI, params)
            print an.windMetersPerSecond_10minAvg,  "m/s"
            print an.windKmph_10minutesAvg, "km/h",  an.windKmph_10minutesAvg * 0.27777777777778
            print an.windKnots_10minAvg, "knot", an.windKnots_10minAvg * 0.51444444444
            print an.gust_metersPerSecond_10minutesAvg, "m/s gust"
            print an.recentGustKmph, "km/h gust", an.recentGustKmph * 0.27777777777778
            print an.recentGustKnots, "knot gust", an.recentGustKnots * 0.51444444444            
#                print 'Wind Direction=\t\t\t %0.2f Degrees' % vane.readWindDirection() 

            print 'Wind Direction=%0.2f Degrees' % vane.averageWindDirection
            temperatureC, temperatureF, pressureHpa, pressureInch, humidity, psea  = bme280.readBME280All()
            print "Temperature        : ", temperatureC, "°C"
            print "Humidity           : ", humidity, "%"
            print "Pressure           : ", pressureHpa, "hPa"
            print "Pressure above sea : ", psea, "hPa"
            print "Altitude above sea : ", bme280.BME280_ALTITUDE, "m"
            if dispayConnected:
                try:
        #            mylcd.lcd_clear()
                    name=birthday()
                    if name:                
                        mylcd.lcd_display_string(' HAPPY BIRTHDAY ',  1)
                        mylcd.lcd_display_string('{:*^16}'.format(' %s '% name), 2)
                        time.sleep(5)
                    mylcd.lcd_display_string('Wind: %0.0f m/s   ' % an.windMetersPerSecond_10minAvg, 1)
                    mylcd.lcd_display_string('Gust: %0.0f m/s   ' % an.gust_metersPerSecond_10minutesAvg, 2)
                    time.sleep(4)            
                    mylcd.lcd_display_string('Temp.: %0.1f %sC     ' % (temperatureC, chr(223)), 1)
                    mylcd.lcd_display_string('Hum. : %0.1f %%     ' % humidity, 2)
        #            mylcd.lcd_display_string('Wind Direction=%0.2f Degrees' % vane.averageWindDirection, 2)
                except Exception as e:
                    print e
                time.sleep(4)
            else:
                time.sleep(5) # 
    except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt      
        pass
    
if __name__ == "__main__":
    main()



