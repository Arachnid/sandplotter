from piclang import *
import logging
import json
import serial
import sandplotter
import time
import urllib

ser = None
p = None


def init_plotter():
  global ser, p
  if ser:
    ser.close()
  ser = serial.Serial('/dev/tty.SandPlotter-DevB', 38400)
  p = sandplotter.SandPlotter(ser)
  return p


def plot_curve(f, points=1000):
  curve = interpolate(f * 5000, points)
  for i in range(len(curve)):
    radius = math.sqrt(curve[i][0] * curve[i][0] + curve[i][1] * curve[i][1]) / 5000.0
    if radius > 1.0:
      curve[i] = (curve[i][0] / radius, curve[i][1] / radius)
  p.plot(curve)

def random_curve():
  data = json.loads(urllib.urlopen("http://sandplotter.appspot.com/random").read())
  logging.warn(data)
  curve = eval(data['formula'])
  plot_curve(curve, data['points'])

def main():
  init_plotter()
  p.set_speed(400)
  p.zero()
  while True:
    p.set_speed(400)
    p.move_xy(-5000, 0)
    p.move_polar(-5000, math.pi * 40)
    p.zero()
    p.set_speed(2000)
    random_curve()
    time.sleep(30)

if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  main()
