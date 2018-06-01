# weather-station
Simple Raspberry Pi weather station (wind speed, wind direction, temperature, humidity, atmospheric pressure)

Based on:
https://github.com/switchdoclabs/SDL_Pi_GroveWeatherPi/blob/master/SDL_Pi_WeatherRack/SDL_Pi_WeatherRack.py
https://www.bosch-sensortec.com/bst/products/all_products/bme280

for some positions the wind vane returns very small voltage diferences 
112.5° => 0.321V
                  voltage difference 0.088V
 67.5° => 0.409V 
                 voltage difference 0.045V
 90.0° => 0.455V 
because of that we have to measure very precisely 
to achive this goal we recalculate voltage measured on voltage divider (wind vane)
voltage, measured on wind vane voltage divider, is Vcc value dependent 
higher Vcc means higher voltage measured on the wind vane voltage divider
using referential Vcc voltage measured on AIN2 pin
