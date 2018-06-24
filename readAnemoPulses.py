#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import division
import RPi.GPIO as GPIO
import time


class Anemometer:
    """Class for reading pulses from the cup rotating anemometer

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
    
    Wind speed should be reported to a resolution of 0.5 m/s or in knots 
    (0.515 m/s) to the nearest unit, and should represent, for synoptic reports,
    an average over 10 min.  

    
    Calibration of the anemometer using GPS is well described here:
    http://www.yoctopuce.com/EN/article/how-to-measure-wind-part-1

    - **parameters**, **types**, **return** and **return types**::

          :param windHistoryInterval: lengtht of the wind history interval in s
          :param pulsesPerRevolution: number of pulses sensor generates per one revolution
          :type windHistoryInterval: int
          :type pulsesPerRevolution: int
          :return: wind speed in knots, m/s, wind gust in knots, m/s
          :rtype: the return type description"""    
    
    def __init__(self,                     
                    windHistoryInterval=60*10, # 10 minutes                     
                    pulsesPerRevolution=2,
                    PIN_ANEM=7, 
                    PIN_SAMPLING_PULSES_OUTPUT=23, 
                    PIN_RPS_SAMPLER_INPUT=24, 
                    minRPM=0,                      
                    maxRPM=3000,
                    SAMPLING_FREQUENCY=4, # 4Hz (input signals are sampled 4 times per second)
                    CALIBRATION_QUOTIENT = 1
                    ):
        
        
        self.rpsQueue=[]
        self.gustQueue=[]
        self.WIND_HISTORY_INTERVAL=windHistoryInterval        
        self.PULSES_PER_REVOLUTION=float(pulsesPerRevolution)                
        self.MIN_RPM=minRPM
        self.MAX_RPM=maxRPM        
        self.SAMPLING_FREQUENCY = SAMPLING_FREQUENCY
        self.meanWindRpm= 0
        self.recentWindGustRpm=0
        self.instantaneousRpm=0
        self._pulseCounter=0
        self.gustInterval = 3*SAMPLING_FREQUENCY         
        self.CALIBRATION_QUOTIENT=CALIBRATION_QUOTIENT
        
        # anemometer pulses generator input
        GPIO.setmode(GPIO.BCM)     
        GPIO.setup(PIN_ANEM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(PIN_ANEM, GPIO.RISING, callback=self._pulseRecorder) 
        
        # sampling frequency generator input
        GPIO.setup(PIN_RPS_SAMPLER_INPUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(PIN_RPS_SAMPLER_INPUT, GPIO.RISING, callback=self._rpsQueueRecorder) 
        
        # sampling frequency generator output
        GPIO.setup(PIN_SAMPLING_PULSES_OUTPUT, GPIO.OUT)
        # create an object q for PWM on port pinPwm at 4 Hertz  (0.25 s sampling frequency)
        self.q = GPIO.PWM(PIN_SAMPLING_PULSES_OUTPUT, SAMPLING_FREQUENCY)
        self.q.start(50)  # start PWM pulses on 50 percent duty cycle


    def _pulseRecorder(self, channel):        
        self._pulseCounter+=1
    
    def _rpsQueueRecorder(self, channel):
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
        self._pulsesCount = self._pulseCounter
        self._pulseCounter=0

    def _maintainQueues(self):
        queueLenght = len(self.rpsQueue)
        windHistoryInterval=self.WIND_HISTORY_INTERVAL*self.SAMPLING_FREQUENCY 
        if queueLenght > windHistoryInterval:
            diff = queueLenght - windHistoryInterval
            del self.rpsQueue[:diff]
            del self.gustQueue[:diff]
            
    def _appendRpsQueue(self):
        # calculate number of pulses per second
        pulsesPerSecond = self._pulsesCount * self.SAMPLING_FREQUENCY
        rps = pulsesPerSecond / self.PULSES_PER_REVOLUTION
        self.rpsQueue.append(rps)
            
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
    
def main():
    WIND_HISTORY_INTERVAL = 60*10 # 10 minutes
    PULSES_PER_REVOLUTION = 2
    PIN_ANEMO=7
    
    an=Anemometer(WIND_HISTORY_INTERVAL, PULSES_PER_REVOLUTION, PIN_ANEMO)
    try:
       while True:
            print an.meanWindRpm,  "mean RPM"
            print an.recentWindGustRpm,  "RPM gust"
            print an.instantaneousRpm, "instanteneous RPM"
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



