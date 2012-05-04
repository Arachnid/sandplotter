from piclang import interpolate
import serial
import sandplotter

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
  p.plot(interpolate(f * 5000, points))
