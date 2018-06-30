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

ADS1115 = 1
REFERENTIAL_VOLTAGE=5000 # 5V


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
        ADS1115 = 1  # 16-bit ADC

        # Select the gain
        self.gain = 6144  # +/- 6.144V
        # self.gain = 4096  # +/- 4.096V

        # Select the sample rate
        self.sps = 250  # 250 samples per second

        # Initialise the ADC using the default mode (use default I2C address)
        # Set this to ADS1015 or ADS1115 depending on the ADC you are using!
        self.ads1115 = ADS1x15(ic=ADS1115, address=0x48)        
        
        self._currentWindDirection=0
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
        # because of that, we have to measure as precise as possible
        # to achive this goal we measure Vcc voltage on the AIN0 pin (referential voltage) 
        # using this value we recalculate voltage measured on the voltage divider (wind vane) AIN1 pin                
        
        # multiple readings  will supperes wind vane turbulent unstability moves
        
        # first reading returns wrong value sometimes, lets read it twice
        self.ads1115.readADCSingleEnded(channel=1, pga=self.gain, sps=self.sps) 
        vaneVoltage = self.ads1115.readADCSingleEnded(channel=1, pga=self.gain, sps=self.sps)  # AIN1 wired to wind vane voltage divider
        
        # first reading returns wrong value sometimes, lets read it twice
        self.ads1115.readADCSingleEnded(channel=0, pga=self.gain, sps=self.sps)  # AIN0 wired to Vcc - referential voltage
        vcc = self.ads1115.readADCSingleEnded(channel=0, pga=self.gain, sps=self.sps)  # AIN0 wired to Vcc - referential voltage    
        calculatedVoltage = (vaneVoltage * (REFERENTIAL_VOLTAGE/vcc))
        return calculatedVoltage/1000, vaneVoltage/1000, vcc/1000
        
        
    def readWindDirection(self):
        calculatedVoltage, vaneVoltage, vcc= self.recentWindDirectionVoltage()
        self._currentWindDirection = self.voltageToDegrees(calculatedVoltage, self._currentWindDirection)
#        print "%0.4f ,%0.4f ,%0.4f, %3.2f" % (vcc,  vaneVoltage,  voltage,  self._currentWindDirection)        
        self.maintainWindDirectionQueue()
        return self.averageWindDirection
        
        
    def maintainWindDirectionQueue(self):
        self._windDirectionQueue.append(self._currentWindDirection)
        queueLenght = len(self._windDirectionQueue)        
        if queueLenght > self._windDirectionHistoryInterval:
            diff = queueLenght - self._windDirectionHistoryInterval
            del self._windDirectionQueue[:diff]            
        # Wind direction should be reported in degrees to the nearest 10°
        self.averageWindDirection = round(self.averagWindDirections(self._windDirectionQueue), -1)
            
        
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
        
    def averagWindDirections(self, listOfAngles):
        sinSum = 0
        cosSum = 0
        for angle in listOfAngles:
            sinSum += math.sin(math.radians(angle))
            cosSum += math.cos(math.radians(angle))
        return ((math.degrees(math.atan2(sinSum, cosSum)) + 360) % 360)        

class Anemometer(object):
    """Class for reading pulses from the cup rotating anemometer

    puls samples has to be recorded/calculated very precisely, because of that: 
    - 4Hz pwm pulses (4 pulses per second) are generated on the output pin
    - pwm signal is wired to the input pin
    - when a rising edge is detected on the input pin, regardless of whatever
      else is happening in the program, the function callback to calculate 
      pulses per second will be run
       
    ***********************************************************
    pulses are recorded according to the 
    WMO GUIDE TO METEOROLOGICAL INSTRUMENTS AND METHODS OF OBSERVATION 
    https://library.wmo.int/opac/doc_num.php?explnum_id=3177
    https://library.wmo.int/pmb_ged/wmo_8_en-2012.pdf
    Recommendations for the design of wind-measuring systems:
    
    Meausrment system consists of an anemometer with a pulse generator that 
    generates pulses at a frequency proportional to the rotation rate of the
    anemometer (preferably several pulses per rotation), a counting device that
    counts the pulses at intervals of 0.25 s, and a microprocessor that computes
    averages and standard deviation over 10 min intervals on the basis of 0.25 s
    samples. 
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

    - **parameters**, **types**, **return** and **return types**::

          :param windHistoryInterval: lengtht of the wind history interval in s
          :param pulsesPerRevolution: number of pulses sensor generates per one revolution
          :type windHistoryInterval: int
          :type pulsesPerRevolution: int
          :return: wind speed in knots, m/s, wind gust in knots, m/s
          :rtype: the return type description"""    
    
    def __init__(self,                     
                    WIND_HISTORY_INTERVAL=60*10, # 10 minutes                     
                    pulsesPerRevolution=2,
                    PIN_ANEMO_PULSES_INPUT=7, 
                    PIN_SAMPLING_PULSES_OUTPUT=23, 
                    PIN_RPS_SAMPLER_INPUT=24, 
                    SAMPLING_FREQUENCY=4, # 4Hz (input signals are sampled 4 times per second)
                    PULSES_TO_MPS_QUOTIENT = 1, 
                    CALIBRATION_QUOTIENT = 1, 
                    minRPM=0,                      
                    maxRPM=3000,
                    ):
        
        self.rpsQueue=[0]
        self.gustQueue=[0]
        self.WIND_HISTORY_INTERVAL=WIND_HISTORY_INTERVAL        
        self.PULSES_PER_REVOLUTION=float(pulsesPerRevolution)                
        self.MIN_RPM=minRPM
        self.MAX_RPM=maxRPM        
        self.SAMPLING_FREQUENCY = SAMPLING_FREQUENCY
        self.meanWindRpm= 0
        self.recentWindGustRpm=0
        self.instantaneousRpm=0        
        self._lastPulsesCount=0
        self.gustInterval = 3*SAMPLING_FREQUENCY         
        self.CALIBRATION_QUOTIENT=CALIBRATION_QUOTIENT
        pi=pigpio.pi()
        
        
        # anemometer pulses generator input
        # when a rising edge is detected on port PIN_ANEMO_PULSES_INPUT, regardless of whatever
        # else is happening in the program, the function callback will be run
        pi.set_pull_up_down(PIN_ANEMO_PULSES_INPUT, pigpio.PUD_DOWN)
        self.cb1=pi.callback(user_gpio=PIN_ANEMO_PULSES_INPUT, edge=pigpio.EITHER_EDGE)
        
        # sampling frequency generator input
        pi.set_pull_up_down(PIN_RPS_SAMPLER_INPUT, pigpio.PUD_DOWN)
        pi.callback(user_gpio=PIN_RPS_SAMPLER_INPUT, edge=pigpio.RISING_EDGE, func=self._rpsQueueRecorder)
        
        # sampling frequency generator output
        pi.hardware_PWM(18, SAMPLING_FREQUENCY, 500000)# start PWM pulses: Broadcom pin 18, 4Hz, 50% dutycycle 

    def _rpsQueueRecorder(self, gpio, level, tick):
        # every time sampling signal occures, average RPS is calculated
        # and appended to the RPS Queue
        self._maintainPulsesCounter()
        self._appendRpsQueue()
        self._apendGustQueue()
        self._maintainQueues()        
        self._meanWind()
        self._gustWind()
        self.instantaneousRpm = self.rpsQueue[-1]*60

    def _maintainPulsesCounter(self):
        pulsesSinceStart = self.cb1.tally()
        self._pulsesCount = pulsesSinceStart-self._lastPulsesCount
        self._lastPulsesCount = pulsesSinceStart
        
    def _appendRpsQueue(self):
        # calculate number of pulses per second
        pulsesPerSecond = self._pulsesCount * self.SAMPLING_FREQUENCY
        rps = pulsesPerSecond / self.PULSES_PER_REVOLUTION        
        self.rpsQueue.append(rps)

    def _maintainQueues(self):
        queueLenght = len(self.rpsQueue)
        windHistoryInterval=self.WIND_HISTORY_INTERVAL*self.SAMPLING_FREQUENCY 
        if queueLenght > windHistoryInterval:
            diff = queueLenght - windHistoryInterval
            del self.rpsQueue[:diff]
            del self.gustQueue[:diff]
            
    def _apendGustQueue(self):
        try:
            recentAverageGust = sum(self.rpsQueue[-self.gustInterval:])/self.gustInterval            
        except IndexError as e:
            recentAverageGust = sum(self.rpsQueue)/len(self.rpsQueue)
        self.gustQueue.append(recentAverageGust)

    def _meanWind(self):
        try:
            averageRps = sum(self.rpsQueue) / len(self.rpsQueue)
            averageRpm = averageRps*60
            self.meanWindRpm = averageRpm
        except ZeroDivisionError as e:            
            self.meanWindRpm = 0
    
    def _gustWind(self):
        self.recentWindGustRpm=max(self.gustQueue)*60
        
def birthday():
    # Easter Egg to display Happy Brithday for your friends on LCD display
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
    WIND_HISTORY_INTERVAL = 60*10 # 10 minutes
    PULSES_PER_REVOLUTION = 2
    PIN_ANEMO_PULSES_INPUT=7
    vane=WindVane()    
    an=Anemometer(WIND_HISTORY_INTERVAL, PULSES_PER_REVOLUTION, PIN_ANEMO_PULSES_INPUT)
    try:
        mylcd = I2C_LCD_driver.lcd(ADDRESS=0X27)
    except IOError as e:
        print e
        
    
    print "===================================="
    try:
        while True:
            print an.meanWindRpm,  "mean RPM"
            print an.recentWindGustRpm,  "RPM gust"
            print an.instantaneousRpm, "instanteneous RPM"
#                print 'Wind Direction=\t\t\t %0.2f Degrees' % vane.readWindDirection() 

            print 'Wind Direction=%0.2f Degrees' % vane.averageWindDirection
            temperature,pressure,humidity,psea = bme280.readBME280All()
            print "Temperature        : ", temperature, "°C"
            print "Humidity           : ", humidity, "%"
            print "Pressure           : ", pressure, "hPa"
            print "Pressure above sea : ", psea, "hPa"
            print "Altitude above sea : ", bme280.altitude, "m"
            try:
    #            mylcd.lcd_clear()
                name=birthday()
                if name:                
                    mylcd.lcd_display_string(' HAPPY BIRTHDAY ',  1)
                    mylcd.lcd_display_string('{:*^16}'.format(' %s '% name), 2)
                    time.sleep(5)
                mylcd.lcd_display_string('Wind: %0.0f m/s   ' % an.meanWindRpm, 1)
                mylcd.lcd_display_string('Gust: %0.0f m/s   ' % an.recentWindGustRpm, 2)
                time.sleep(4)            
                mylcd.lcd_display_string('Temp.: %0.1f %sC     ' % (temperature, chr(223)), 1)
                mylcd.lcd_display_string('Hum. : %0.1f %%     ' % humidity, 2)
    #            mylcd.lcd_display_string('Wind Direction=%0.2f Degrees' % vane.averageWindDirection, 2)
            except UnboundLocalError as e:
                print e
            time.sleep(4)
    except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt      
        pass
    



if __name__ == "__main__":
    main()



