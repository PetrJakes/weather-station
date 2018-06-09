#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# SDL_Pi_WeatherRack Example Test File
# Version 1.0 February 12, 2015
#
# SwitchDoc Labs
# www.switchdoc.com
# modified by Petr Jakes
# 8.6.2018
#

import time
import sys
import bme280

import config
import SDL_Pi_WeatherRack as SDL_Pi_WeatherRack


# GPIO Numbering Mode GPIO.BCM
anenometerPin = 7
rainPin = 21

# constants
SDL_MODE_INTERNAL_AD = 0 # using internal A/D converter for voltage reading
SDL_MODE_I2C_ADS1015 = 1 # using ADS1x15 for voltage reading

# wind speed sampling constants
# sample mode means return immediately.  THe wind speed is averaged at samplingInterval or when you ask, whichever is longer
SDL_MODE_SAMPLE = 0

# Delay mode means to wait for samplingInterval and the average after that time.
# BUG, not working
SDL_MODE_DELAY = 1


# adcContinuousConversion sets ADC to the continuous reading
# multiple voltage values are read, median function is used to find returned value
weatherStation = SDL_Pi_WeatherRack.SDL_Pi_WeatherRack(
                                                                anenometerPin, rainPin, 
                                                                intAnem=0, intRain=0, 
                                                                ADMode=SDL_MODE_I2C_ADS1015, 
                                                                adcContinuousConversion=0
                                                                )
weatherStation.setWindReadingMode(SDL_MODE_SAMPLE, samplingInterval=1.0) # sampling interval in seconds
#weatherStation.setWindReadingMode(SDL_MODE_DELAY, samplingInterval=2.0)


maxEverWind = 0.0
maxEverGust = 0.0
totalRain = 0
shall =0
while True:
#    print '---------------------------------------- '
#    print '----------------- '
#    print ' SDL_Pi_WeatherRack Library'
#    print ' WeatherRack Weather Sensors'
#    print '----------------- '

    currentWindSpeed = weatherStation.current_wind_speed() / 1.609 # converting to mph
    currentWindGust = weatherStation.get_wind_gust() / 1.609
#    totalRain = totalRain + weatherStation.get_current_rain_total() / 25.4
#    print 'Rain Total=\t%0.2f in' % totalRain
    print 'Wind Speed=\t%0.2f MPH' % currentWindSpeed
    if currentWindSpeed > maxEverWind:
        maxEverWind = currentWindSpeed

    if currentWindGust > maxEverGust:
        maxEverGust = currentWindGust
    print 'max Ever Wind Speed=\t%0.2f MPH' % maxEverWind
    print 'MPH wind_gust=\t%0.2f MPH' % currentWindGust
    print 'max Ever Gust wind_gust=\t%0.2f MPH' % maxEverGust
    print 'Wind Direction=\t\t\t %0.2f Degrees' % weatherStation.current_wind_direction()    
    print "===================================="
#    temperature,pressure,humidity,psea = bme280.readBME280All()
#    print "Temperature        : ", temperature, "C"
#    print "Humidity           : ", humidity, "%"
#    print "Pressure           : ", pressure, "hPa"
#    print "Pressure above sea : ", psea, "hPa"
#    print "Altitude above sea : ", bme280.altitude, "m"
    #    print '----------------- '
    #    print '----------------- '

    time.sleep(1)
