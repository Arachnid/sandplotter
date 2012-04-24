#! /usr/bin/env python

import logging
import math
import sys
import serial
import time

import sandplotter


logging.basicConfig(level=logging.DEBUG)


def generate_hypotrochoid(p, q, radius, steps_per_rad=10):
    a = 1.0
    b = float(p) / q
    period = 2 * math.pi * p
    scale = radius / (a + 2 * b)
    
    for i in range(1, int(period * steps_per_rad)):
        t = float(i) / steps_per_rad
        x = (a + b) * math.cos(t) + b * math.cos((a + b) / b * t)
        y = (a + b) * math.sin(t) + b * math.sin((a + b) / b * t)
        yield x * scale, y * scale


def main(args):
    port = args[0]
    baud = int(args[1])
    p = int(args[2])
    q = int(args[3])
    radius = int(args[4])
    speed = int(args[5])
    
    socket = serial.Serial(port, baud)
    time.sleep(1.0) # Give the bootloader a chance to exit

    plotter = sandplotter.SandPlotter(socket, debug=True)
    plotter.set_speed(speed)
    
    for x, y in generate_hypotrochoid(p, q, radius):
        plotter.move_xy(int(x), int(y))


if __name__ == '__main__':
    main(sys.argv[1:])
