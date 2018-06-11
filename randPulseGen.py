#!/usr/bin/python
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import random


pwmPin = 8
MIN_FREQUENCY = 0 # pulses per second
MAX_FREQUENCY = 40 # pulses per second

GPIO.setmode(GPIO.BCM) # GPIO Numbering Mode Broadcom
GPIO.setup(pwmPin, GPIO.OUT)
p = GPIO.PWM(pwmPin, 50) # create an object p for PWM on port pwmPin at 50 Hertz  
p.start(50)  # start the PWM on 50 percent duty cycle  
#p.ChangeFrequency(100)  # change the frequency to 100 Hz (floats also work) e.g. 100.5, 5.2  

  

try:  
    while True:  
        ran=random.randint(MIN_FREQUENCY, MAX_FREQUENCY)
        p.ChangeFrequency(100)
        ran = ran.randint(1, 10)
        sleep(ran)                 # wait randomly        
  
except KeyboardInterrupt:          # trap a CTRL+C keyboard interrupt  
    p.stop()                # stop the PWM output    
    GPIO.cleanup()         # when your program exits, tidy up after yourself  
    
