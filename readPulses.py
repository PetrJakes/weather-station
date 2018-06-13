#!/usr/bin/python
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import random
import time

import numpy as np

PIN_TEST=7
MEASURED_INTERVAL = 60*10
#MEASURED_INTERVAL = 10
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_TEST, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


tickHistory = np.array([])
def addTimeStamp(channel):
    global tickHistory
    tickTime=time.time()
    tickHistory = np.append(tickHistory , tickTime)
    if tickTime - MEASURED_INTERVAL > tickHistory[0]:
        tickHistory=tickHistory[tickHistory>(tickTime - MEASURED_INTERVAL)]        

GPIO.add_event_detect(PIN_TEST, GPIO.RISING, callback=addTimeStamp) 
time.sleep(1)
try:
    while True:        
        print tickHistory[-1]-tickHistory[-2], tickHistory[-1]
        print len(tickHistory)
        time.sleep(2)
except KeyboardInterrupt:          # trap a CTRL+C keyboard interrupt      
    GPIO.cleanup()         # when your program exits, tidy up after yourself  
print len(tickHistory)


