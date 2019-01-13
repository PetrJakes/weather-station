#!/usr/bin/python
# -*- coding: utf-8 -*-
# script for testing the resistance of the wind vane wiring
# the length of the wind vane wiring and the quality of RJ11 connector
# can affect the results while measuring wind wane resistance

from weather import WindVane
vane=WindVane(test=True)
print "Set the the wind vane pointer to the North."
print "It means the round part of the pointer ( %s%s%s%s%s )" % (u'\u2501',u'\u2500', u'\u252c', u'\u2500',  u'\u3007')
print "is positioned to the fixed cable and the tick part of the pointer"
print "is positioned to the RJ11 female connector"

raw_input('Press enter to continue: ')
calculatedVoltage, vaneVoltage, vcc =  vane.recentWindDirectionVoltage()
vCoeficient = format((3.83721-calculatedVoltage), '.5f')
strCalculatedVoltage=format(calculatedVoltage, ".5f")
print "expected voltage: %s V" % str(3.83721)
print "measured voltage: %s V" % strCalculatedVoltage
if float(vCoeficient) > 0.1:
    print "voltage coef = %s" % vCoeficient
    print "change the VOLTAGE_COEF value in the weater.ini file to %s" % vCoeficient    
if calculatedVoltage >= 3.63433 and calculatedVoltage < 3.93894:    
    print "measured voltage OK!"
    print "no user acction necessary"
    
    
    
