#!/usr/bin/python
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import random
import time

import numpy as np

PIN_TEST=7
HISTORY_LENGHT = 60*10 # 10 minutes
GUST_HISTORY_LENGHT= 60*2 # 2 minutes
#HISTORY_LENGHT = 10
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_TEST, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#pulsesHistory = np.array([])
#pulsesHistory = np.append(pulsesHistory , time.time())

lastPulseTime = time.time()
pulsesHistory = [lastPulseTime]
pulsesDiffHistory=[]
gustPulsesHistory=[lastPulseTime]
gustPulsesDiffHistory=[]

class SDL_Pi_WeatherRack:
    def __init__(self):
        pass

def keepPulseHistory(channel):
    global lastPulseTime
    global pulsesHistory
    global pulsesDiffHistory
    global gustPulsesHistory
    global gustPulsesHistory    
    pulseTime=time.time()
#    pulsesHistory = np.append(pulsesHistory , pulseTime)
    if lastPulseTime!=pulseTime:        
        pulsesHistory.append(pulseTime)
        gustPulsesHistory.append(pulseTime)
        pulsesDiffHistory.append(pulseTime-lastPulseTime)
        gustPulsesDiffHistory.append(pulseTime-lastPulseTime)
        while pulsesHistory[0] < (pulseTime - HISTORY_LENGHT):
            pulsesHistory.pop(0)
            pulsesDiffHistory.pop(0)
    
        while gustPulsesHistory[0] < (pulseTime - GUST_HISTORY_LENGHT):
            gustPulsesHistory.pop(0)
            gustPulsesDiffHistory.pop(0)
            
        lastPulseTime = pulseTime

def getShorterHistory(period):
    shortPulsesHistory=pulsesHistory[pulsesHistory>(pulseTime - period)]  # https://www.dataquest.io/blog/numpy-cheat-sheet/
    pass

GPIO.add_event_detect(PIN_TEST, GPIO.RISING, callback=keepPulseHistory) 
time.sleep(1)
try:
    while True:        
#        print time.time()-pulsesHistory[-1]
        print len(pulsesHistory),  len(pulsesDiffHistory)        
        print max(pulsesDiffHistory),  min(pulsesDiffHistory)
        time.sleep(5)
except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt      
    GPIO.cleanup()          # when your program exits, tidy up after yourself  
print len(pulsesHistory)


