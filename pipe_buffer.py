# -*- coding: utf-8 -*-

import fcntl
import os

from splicy.splice import F_SETPIPE_SZ, F_GETPIPE_SZ


class PipeBuffer(object):

    PIPE_BUFFER_SIZE = 2**20

    def __init__(self, size = PIPE_BUFFER_SIZE):
        # FIXME: in case of EMFILE when calling os.pipe(), self.reader
        # and self.writer can be uninitialised, which will raise an
        # AttributeError in __del__()
        self.reader, self.writer = os.pipe()
        self.size = size

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        # FIXME: self._size is not the *real* size of the buffer
        self._size = value
        return fcntl.fcntl(self.reader, F_SETPIPE_SZ, value)

    def write(self, data):
        return os.write(self.writer, data)

    def read(self, buffersize):
        return os.read(self.reader, buffersize)

    def close(self):
        try:
            os.close(self.reader)
        finally:
            os.close(self.writer)
