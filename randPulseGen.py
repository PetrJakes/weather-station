#!/usr/bin/python
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import random
import time

pinPwm = 8
MIN_FREQUENCY = 2 # pulses per second
MAX_FREQUENCY = 70 # pulses per second

GPIO.setmode(GPIO.BCM) # GPIO Numbering Mode Broadcom

GPIO.setup(pinPwm, GPIO.OUT)
p = GPIO.PWM(pinPwm, 1) # create an object p for PWM on port pinPwm at 50 Hertz  
p.start(50)  # start the PWM on 50 percent duty cycle  
#p.ChangeFrequency(100)  # change the frequency to 100 Hz (floats also work) e.g. 100.5, 5.2  
#p.ChangeDutyCycle(90)

#GPIO.setup(23, GPIO.OUT)
#q = GPIO.PWM(23, 0.5) # create an object p for PWM on port pinPwm at 1 Hertz  
#q.start(50)  # start the PWM on 50 percent duty cycle  

try:  
    while True:  
#        ran=random.randint(MIN_FREQUENCY, MAX_FREQUENCY)
#        p.ChangeFrequency(ran)
        ran = random.randint(5,120)
        time.sleep(ran)                 # wait randomly        
  
except KeyboardInterrupt:          # trap a CTRL+C keyboard interrupt  
    p.stop()                # stop the PWM output    
    GPIO.cleanup()         # when your program exits, tidy up after yourself  
    
