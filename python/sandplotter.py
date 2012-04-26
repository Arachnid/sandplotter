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

    def move_xy(self, x, y):
        self._write("m %d %d\n" % (x, y))
        self._read_ok()

    def move_polar(self, r, theta):
        self._write("p %d %d\n" % (r, theta))
        self._read_ok()

    def set_speed(self, speed):
        self._write("s %d\n" % (speed,))
        self._read_ok()

    def zero(self):
        self._write("0\n")
        self._read_ok()
