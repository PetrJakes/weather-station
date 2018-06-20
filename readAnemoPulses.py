#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import division
import RPi.GPIO as GPIO
import time


class Anemometer:    
    GPIO.setmode(GPIO.BCM)     
    GPIO.setup(23, GPIO.OUT)
    # create an object q for PWM on port pinPwm at 0.33 Hertz  (wind speed sampling frequency)
#    q = GPIO.PWM(23, 1.0/3) 
    q = GPIO.PWM(23, 1) 
    q.start(50)  # start the PWM on 50 percent duty cycle  
    
    def __init__(self,                     
                    windHistoryInterval=60*10,                     
                    pulsesPerRevolution=2,
                    PIN_ANEM=7, 
                    PIN_RPS_RECORDER=24, 
                    minRPM=0,                      
                    maxRPM=3000,
                    ):
        
        self.pulsesQueue = []
        self.rpsQueue=[]
        self.WIND_HISTORY_INTERVAL=windHistoryInterval        
        self.PULSES_PER_REVOLUTION=float(pulsesPerRevolution)        
        self.lastKnownPulseTime=time.time()
        self.MIN_RPM=minRPM
        self.MAX_RPM=maxRPM
        self.MAX_RPS=maxRPM/60
        self.meanWind= 0
        self.recentWindGust=0
        
        GPIO.setup(PIN_ANEM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(PIN_ANEM, GPIO.RISING, callback=self._pulseRecorder) 
        
        GPIO.setup(PIN_RPS_RECORDER, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(PIN_RPS_RECORDER, GPIO.RISING, callback=self._rpsQueueRecorder) 
        ##        

    def _pulseRecorder(self, channel):        
        # pulses from anemometer are recorded as timestamps
        pulseTime=time.time()    
        self.pulsesQueue.append(pulseTime)        
    
    def _rpsQueueRecorder(self, channel):
        """from recorded timestamps a rps que """
        self._maintainPulsesQueue()
        if len(self.recentPulsesQueue)>1:            
            numberOfRotation=len(self.recentPulsesQueue)/self.PULSES_PER_REVOLUTION  
            dutyTime=(self.recentPulsesQueue[-1]- self.recentPulsesQueue[0])
#            print "duty time:",  dutyTime
            averageRps = numberOfRotation/dutyTime
            if averageRps > self.MAX_RPS: 
                # to eliminate false short pulses
                self.rpsQueue.append(0)
            else:
                self.rpsQueue.append(averageRps)
        else:
            self.rpsQueue.append(0)
        self._maintainAverageRpsQueue()
        self._meanWind()
        self._gustWind()
        self.instantaneousRps = self.rpsQueue[-1]

    def _maintainAverageRpsQueue(self):
        queueLenght = len(self.rpsQueue)
        if queueLenght > self.WIND_HISTORY_INTERVAL:
            diff = queueLenght - self.WIND_HISTORY_INTERVAL
            del self.rpsQueue[:diff]

    def _maintainPulsesQueue(self):
        self.recentPulsesQueue = self.pulsesQueue            
        self.pulsesQueue=[]
        
    def _meanWind(self):
        try:
            averageRpm=(sum(self.rpsQueue) / len(self.rpsQueue))*60
        except ZeroDivisionError as e:            
            self.meanWind = 0
        self.meanWind = averageRpm
    
    def _gustWind(self):
        gusts=[]
        for i in range(len(self.rpsQueue)):
            try:
                gusts.append(sum(self.rpsQueue[i:i+3])/3)
            except IndexError as e:
                pass
        if gusts:
            self.recentWindGust=max(gusts)
        else:
            self.recentWindGust=0

def main():
    PIN_ANEMO=7
    WIND_HISTORY_INTERVAL = 60*10 # 10 minutes    
    PULSES_PER_REVOLUTION = 2
    
    an=Anemometer(WIND_HISTORY_INTERVAL, PULSES_PER_REVOLUTION, PIN_ANEMO)
    try:
       while True:
            print an.meanWind,  "RPM"
            print an.recentWindGust
#            try:
#                avg = an.averageRpm()
#                print "average rpm:", avg
#                
#            except Exception as e:
#                print e
##                print "*****main*****"
##                print e
            time.sleep(3)
    except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt      
        GPIO.cleanup()          # when your program exits, tidy up after yourself  
    print an.rpsQueue[-1]



if __name__ == "__main__":
    main()



