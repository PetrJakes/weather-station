#!/usr/bin/python
# -*- coding: utf-8 -*-
import serial
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
            # prijaty checksum prevedeme do stjeneho formatu jako spocitany 
            # checksum a porovname; checksum is calculated as the XOR of 
            # bytes between (but not including) the dollar sign ($GPRMC)
            # and asterisk (*68)                
            if calculatedChecksum(txtLine[1:-3]) ==  int(receivedChecksum,16):                
#                print lineList[7] # Speed over the ground in knots
                return str(float(lineList[7])*1.85200*0.27777777777778) # mps
        elif lineList[2]=='V':
            log = "GPS 'not fixed'"            
            return log
                

#port = '/dev/ttyUSB0'
port = '/dev/ttyACM0'

WIND_HISTORY_INTERVAL = 60*10 # 10 minutes
PULSES_PER_REVOLUTION = 2
PIN_ANEMO_PULSES_INPUT=7
an=Anemometer(WIND_HISTORY_INTERVAL, PULSES_PER_REVOLUTION, PIN_ANEMO_PULSES_INPUT)
f = open('./gps.log', "w+")
try:
    while True:
        with serial.Serial(port, baudrate=9600, timeout=1) as ser:
            gpsLine = ser.readline()
            if gpsLine.startswith("$GPRMC"):
                gpsLine = gpsLine.strip()
                speed = analyzeGPRMCsentence(gpsLine)
                print speed, "mps", an.rpsQueue[-1],  "rpm"
                if speed != "GPS 'not fixed'":                    
                    f.write("%s,%s\n" % (speed, str(an.rpsQueue[-1])))
except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt      
    GPIO.cleanup()          # when your program exits, tidy up after yourself  
