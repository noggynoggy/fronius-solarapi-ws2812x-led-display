#!/usr/bin/env python3
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.

import time
from rpi_ws281x import *
import argparse
import requests
import json
import colorsys
import pickle
from PIL import ImageColor
from datetime import datetime
from pytz import timezone
from suntime import Sun


# LED strip configuration:
LED_COUNT      = 104    # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating a signal (try 10)
LED_BRIGHTNESS = 65      # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
dim = 0.3
dim_night = 0.1
max_consumption = 10000
get_delay = 2
get_times = 1
##########

def get_bat():
    url = 'http://192.168.178.62/solar_api/v1/GetStorageRealtimeData.cgi'
    params = {
        'Scope': 'Device',
        'DeviceId': 0
    }

    response = requests.get(url, params=params)
    json_data = response.json()

    return json_data['Body']['Data']['Controller']

def get_grid_solar_and_consumption():
    url = 'http://192.168.178.62/solar_api/v1/GetPowerFlowRealtimeData.fcgi'
    params = {}

    response = requests.get(url, params=params)
    json_data = response.json()

    return int(json_data['Body']['Data']['Site']['P_Grid']), int(json_data['Body']['Data']['Site']['P_PV']), int(json_data['Body']['Data']['Inverters']['1']['P'])

##################################################

# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, area ,wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in area:
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0)

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbowCycle(strip, wait_ms=20, iterations=5):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

################################################

def get_bat_color(bat_change, bat_percentage, dim):
    if bat_percentage > 0.98:
        return Color(0,int(100*dim),int(255*dim))

    mid_h = 50  # yellow
    max_change_watts = 4500
    max_change_h = 50
    def hls_to_rgb(hls):
        # Convert HLS values to RGB values
        rgb = colorsys.hls_to_rgb(hls[0]/360, hls[2]/100, hls[1]/100)
        # Scale RGB values to 0-255 range
        rgb = tuple(int(val * 255) for val in rgb)
        return rgb

    h_change = (bat_change / max_change_watts) * max_change_h
    h = mid_h + h_change
    r, g, b = hls_to_rgb((h, 100, 50))
    r = int(r * dim)
    g = int(g * dim)
    b = int(b * dim)
    return Color(r, g, b)

def get_bat_coverage(bat_percentage):
    mid = int(LED_COUNT//2)
    return range(mid, int(mid - (mid * bat_percentage)), -1)

#################################################

def get_grid_color(grid, dim):
    if grid > 0:
        return Color(int(255*dim), 0, 0)
    else:
        return Color(0, 0, int(255*dim))

def get_grid_length(grid, max_consumption):
    return int((abs(grid) / max_consumption) * (LED_COUNT//2))

def get_solar_length(solar_to_display, max_consumption):
    return int((solar_to_display / max_consumption) * (LED_COUNT//2))

def get_bat_length(bar_change_to_display, max_consumption):
    return int((abs(bat_change_to_display) / max_consumption) * (LED_COUNT//2))

def get_solar_color(solar, dim):
    r = int(255 * dim)
    g = int(255 * dim)
    b = 0
    return Color(r,g,b)


#############################################

def fake(grid, solar, consumption, bat_change, bat_percentage):
    grid           = grid
    solar          = solar
    consumption    = consumption
    bat_change     = bat_change
    bat_percentage = bat_percentage
    return grid, solar, consumption, bat_change, bat_percentage


if __name__ == '__main__':
    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    try:

        latitude = 0
        longitude = 0

        cet_timezone = timezone('CET')

        current_time_cet = datetime.now(cet_timezone)

       # current_time_cet = current_time_cet.replace(hour=14)
        if current_time_cet.hour >= 23 or current_time_cet.hour < 6:
            for i in range(LED_COUNT):
                strip.setPixelColor(i, 0)
                strip.show()
                exit(0)

        sun = Sun(latitude, longitude)

        today_sr = sun.get_sunrise_time().replace(tzinfo=cet_timezone)
        today_ss = sun.get_sunset_time().replace(tzinfo=cet_timezone)

        if today_sr > current_time_cet or current_time_cet > today_ss:
            dim = dim_night

        # GET VALUES
        grid, solar, consumption = get_grid_solar_and_consumption()
        bat = get_bat()
        bat_change = int(bat['Voltage_DC'] * bat['Current_DC'])
        bat_percentage = bat['StateOfCharge_Relative'] / 100
        print(">0> ", grid, solar, consumption, bat_change, bat_percentage)

        for r in range(get_times-1):
            time.sleep(get_delay)
            grid_2, solar_2, consumption_2 = get_grid_solar_and_consumption()
            grid = grid + grid_2
            solar = solar + solar_2
            consumption = consumption + consumption_2
            bat = get_bat()
            bat_change = bat_change + int(bat['Voltage_DC'] * bat['Current_DC'])
            bat_percentage = bat_percentage + bat['StateOfCharge_Relative'] / 100
            print(f">{r+1}> ",grid, solar, consumption, bat_change, bat_percentage)

        grid = grid // get_times
        solar = solar // get_times
        consumption = consumption / get_times

        print(">>> ", grid, solar, consumption,  bat_change, bat_percentage)
        if grid < 0:
            consumption = consumption + grid # cons - grid
        print(">>> ", grid, solar, consumption,  bat_change, bat_percentage)

        bat_change = bat_change // get_times
        bat_percentage = bat_percentage / get_times

        # ENABLBE TESTING
        grid, solar, consumption, bat_change, bat_percentage = fake(grid, solar, consumption, bat_change, bat_percentage)
        #bat_percentage = 0.99

        f = open("/home/pi/led/history.pickle", "rb")
        history = pickle.load(f)
        f.close()

#        bat_percentage = 1.0

        # RAINBOW MOTHEEFUCKERS
        if all(h < 0.98 for h in history) and (bat_percentage > 0.98):
            rainbowCycle(strip,wait_ms=5, iterations=10)
            for i in range(LED_COUNT):
                strip.setPixelColor(i, 0)


        for i in range(len(history)-2, -1, -1):
            history[i+1] = history[i]
        history[0] = bat_percentage

        f = open("/home/pi/led/history.pickle", "wb")
        pickle.dump(history, f)
        f.close()

        # Do Bat
        bat_color = get_bat_color(bat_change, bat_percentage, dim)
        bat_coverage = get_bat_coverage(bat_percentage)
        for i in bat_coverage:
            strip.setPixelColor(i, bat_color)

        if consumption > solar:
            solar_to_display      = solar
            bat_change_to_display = bat_change
        else:
            solar_to_display      = consumption
            bat_change_to_display = 0

        i = 0
        j = 0
        k = 0

        # Do Consupotion
        mid = LED_COUNT//2 +1
        for i in range(mid, mid + get_solar_length(solar_to_display, max_consumption)):
            strip.setPixelColor(i, Color(int(255*dim), int(255*dim), 0))

        if i == 0: i = mid
        for j in range(i, i + get_bat_length(bat_change_to_display, max_consumption)):
            strip.setPixelColor(j, Color(0, int(255 * dim), 0))

        if j == 0:
            if i == 0:
               j = mid
            else:
               j = i

        for k in range(j, j + get_grid_length(grid, max_consumption)):
            strip.setPixelColor(k, get_grid_color(grid, dim))


        mid_color = Color(int(255*dim), int(255*dim), int(255*dim))
        strip.setPixelColor(mid-1, mid_color)
        #strip.setPixelColor(52, Color(255, 255, 255))
        # SHOW
        strip.show()

    except KeyboardInterrupt:
        print("\nSIGINT OK")
        exit(0)
