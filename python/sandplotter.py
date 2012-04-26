import logging

class Error(Exception): pass

class UnexpectedResponseError(Error):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return "Got unexpected response '%s'" % (self.response,)


class SandPlotter(object):
    def __init__(self, socket, debug=False):
        self._socket = socket
        self._debug = debug
        self._get_info()

    def _write(self, data):
        if self._debug:
            logging.debug("> %r", data)
        self._socket.write(data)

    def _readline(self):
        while True:
            result = self._socket.readline()
            if not result.startswith("LOG "):
                break
            logging.debug(result)
        if self._debug:
            logging.debug("< %r", result)
        return result

    def _read_ok(self):
        result = self._readline().strip()
        if result != "OK":
            raise UnexpectedResponseError(result)

    def _get_info(self):
        self._write("?\n");
        result = self._readline().strip()
        result_parts = result.split(" ")
        if len(result_parts) < 5:
            raise UnexpectedResponseError(result)
        status, theta_steps, max_r, theta, r = result[:3]
        if status != 'INFO':
            raise UnexpectedResponseError(result)
        self.steps_per_circle = int(theta_steps)
        self.steps_per_radian = self.steps_per_circle / (math.pi * 2)
        self.max_radius = int(max_r)
        self._theta = int(theta)
        self.radius = int(r)

    @property
    def theta(self):
        return self._theta / self.steps_per_radian

    def move_xy(self, x, y):
        self._write("m %d %d\n" % (x, y))
        self._read_ok()
        self.radius = int(math.sqrt(x * x + y * y))
        self._theta = math.atan2(y, x)

    def move_polar(self, radius, theta):
        step_theta = int(theta * self.steps_per_radian)
        self._write("p %d %d\n" % (radius, step_theta))
        self._read_ok()
        self.radius += radius
        self._theta = (self._theta + step_theta) % self.steps_per_circle

    def set_speed(self, speed):
        self._write("s %d\n" % (speed,))
        self._read_ok()

    def zero(self):
        self._write("0\n")
        self._read_ok()

    def noop(self):
        self._write("n\n")
        self._read_ok()
