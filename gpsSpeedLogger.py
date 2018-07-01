#!/usr/bin/python
# -*- coding: utf-8 -*-
import serial
import time
from readAnemoPulses import Anemometer

def calculatedChecksum(s):    
    result = 0
    for character in s:
        result ^= ord(character)
    return result 
    
    
def analyzeGPRMCsentence(txtLine):          
    lineList=txtLine.split(',')    
    if len(lineList) > 12: # all words of the GPRMC sentence are read        
        if lineList[2]=='A' and '*' in lineList[-1]:
#            print lineList
            receivedChecksum = lineList[12][2:]
            # change the format of recieved checksum to the format of calculated
            # checksum and compare;
            # checksum is calculated as the XOR of bytes between (but not including)
            # the dollar sign ($GPRMC) and asterisk (*68)                
            if int(receivedChecksum,16) ==  calculatedChecksum(txtLine[1:-3]):
               # lineList[7] Speed over the ground in knots
                return str(float(lineList[7])*0.51444444444) # knots to mps
        elif lineList[2]=='V':
            log = "GPS 'not fixed'"            
            return log
                

#port = '/dev/ttyUSB0'
port = '/dev/ttyACM0'

WIND_HISTORY_INTERVAL = 60*10 # 10 minutes
PULSES_PER_REVOLUTION = 4

PIN_ANEMO_PULSES_INPUT=22

PIN_SAMPLING_PULSES_OUTPUT= 18 # Start hardware PWM on a PIN_SAMPLING_PULSES_OUTPUT GPIO (dutycycle 50% set in the code)
SAMPLING_FREQUENCY= 1 # Hz (1 Hz means rps is calculated 1 times per second)
PIN_RPS_SAMPLER_INPUT= 23 


an=Anemometer(WIND_HISTORY_INTERVAL, PULSES_PER_REVOLUTION, PIN_ANEMO_PULSES_INPUT, PIN_SAMPLING_PULSES_OUTPUT, PIN_RPS_SAMPLER_INPUT, SAMPLING_FREQUENCY)
time.sleep(1)
f = open('./gpslog.csv', "a+")
try:
    while True:
        with serial.Serial(port, baudrate=9600, timeout=1) as ser:
            gpsLine = ser.readline()
            if gpsLine.startswith("$GPRMC"):
                gpsLine = gpsLine.strip()
                speed = analyzeGPRMCsentence(gpsLine)
                rps = str(an.rpsQueue[-1])
                print an._pulsesCount
                print speed, "mps", rps,  "rps"
                if speed != "GPS 'not fixed'":                    
                    f.write("%s,%s\n" % (speed, rps))
except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt    
    pi.stop()
    print "finished"
