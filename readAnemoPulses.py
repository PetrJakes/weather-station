#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import division
import RPi.GPIO as GPIO
import random
import time

import numpy as np


#WIND_HISTORY_INTERVAL = 10
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(PIN_ANEMO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#pulsesHistory = np.array([])
#pulsesHistory = np.append(pulsesHistory , time.time())



class Anemometer:
    GPIO.setmode(GPIO.BCM)
    
    def __init__(self, pinAnem, windHistoryInterval=60*10, gustHistoryInterval=60*3, pulsesPerRevolution=2, minRpm=0):
        self.pulsesHistory = []
        self.pulsesDiffHistory=[]
        self.gustPulsesHistory=[]
        self.gustPulsesDiffHistory=[]
        self.WIND_HISTORY_INTERVAL=windHistoryInterval
        self.GUST_HISTORY_INTERVAL=gustHistoryInterval
        self.PULSES_PER_REVOLUTION=float(pulsesPerRevolution)
        self.minRpm=minRpm
        self.lastKnownRps=0
#        self.lastPulseTime = time.time()
        GPIO.setup(pinAnem, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(pinAnem, GPIO.RISING, callback=self._keepPulseHistory) 
        
        
    def _keepPulseHistory(self, channel):        
        pulseTime=time.time()    
        self.pulsesHistory.append(pulseTime)
        self.gustPulsesHistory.append(pulseTime)
        try:
            self.pulsesDiffHistory.append(pulseTime-self.lastPulseTime)
            self.gustPulsesDiffHistory.append(pulseTime-self.lastPulseTime)
        except AttributeError as e:            
            pass
        
        while self.pulsesHistory[0] < (pulseTime - self.WIND_HISTORY_INTERVAL):
            self.pulsesHistory.pop(0)
            self.pulsesDiffHistory.pop(0)        
        while self.gustPulsesHistory[0] < (pulseTime - self.GUST_HISTORY_INTERVAL):
            self.gustPulsesHistory.pop(0)
            self.gustPulsesDiffHistory.pop(0)                
        self.lastPulseTime = pulseTime        
            
    def averageRpm(self):
        numberOfRotation=len(self.pulsesHistory)/self.PULSES_PER_REVOLUTION        
        try:            
            durationOfRotation=(self.pulsesHistory[-1] - self.pulsesHistory[0])
            rps = numberOfRotation/durationOfRotation
            if rps == self.lastKnownRps:
                return 0            
        except (ZeroDivisionError, IndexError) as e:
            print e
            return 0        
        self.lastKnownRps=rps
        return rps*60

    def meanWind(self):
        pass



def main():
    PIN_ANEMO=7
    WIND_HISTORY_INTERVAL = 60*10 # 10 minutes
    GUST_HISTORY_INTERVAL= 60*2 # 2 minutes
    PULSES_PER_REVOLUTION = 2
    
    an=Anemometer(PIN_ANEMO, WIND_HISTORY_INTERVAL, GUST_HISTORY_INTERVAL, PULSES_PER_REVOLUTION)
    try:
        while True:        
            try:
                print an.averageRpm(), "rpm"
                time.sleep(5)
            except Exception as e:
                print e
    except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt      
        GPIO.cleanup()          # when your program exits, tidy up after yourself  
    print len(an.pulsesHistory)



if __name__ == "__main__":
    main()



