# -*- coding: utf-8 -*-

import socket

from pyev import EV_READ, EV_WRITE
from cyhttp11 import HTTPParser

from splicy.pipe_buffer import PipeBuffer
from splicy.splice import splice


class InboundClient(object):

    IO_TIMEOUT = 10
    MAX_REQUEST_SIZE = 4096

    def __init__(self, server, loop, sock, address_info):
        self.server = server
        self.loop = loop
        self.sock = sock
        self.sock.setblocking(0)
        self.address_info = address_info
        self.pipe_buffer = PipeBuffer()
        self.watchers = {
            'recv': loop.io(sock.fileno(), EV_READ, self.recv_data),
            'send': loop.io(sock.fileno(), EV_WRITE, self.send_data, 0),
            'timeout': loop.timer(self.IO_TIMEOUT, self.IO_TIMEOUT,
                                  self.timeout),
            }
        self.http_parser = HTTPParser()

    def start(self):
        self.watchers['recv'].start()
        self.watchers['timeout'].start()
        # send is not started yet

    def stop(self):
        for watcher in self.watchers.values():
            watcher.stop()
        self.sock.close()
        self.pipe_buffer.close()
        self.server.remove_client(self)
        self.server.logger.debug('Stopped client: %s', self)

    def recv_data(self, watcher, revents):
        try:
            data = self.sock.recv(self.MAX_REQUEST_SIZE, socket.MSG_PEEK)
            self.http_parser.execute(data)
            if self.http_parser.has_error():
                self.stop()
            elif self.http_parser.is_finished():
                # IO_TIMEOUT seconds at most for the response to come in
                self.watchers['timeout'].reset()
                data = self.sock.recv(self.MAX_REQUEST_SIZE)
                # We're not interested in any more data from this peer
                self.sock.shutdown(socket.SHUT_RD)
                watcher.stop()
                # Ask our server for the response, cached or not
                self.server.proxy(self, self.http_parser, data)
        except:
            self.server.logger.exception('While recv_data():')
            raise

    def start_sending(self):
        self.watchers['send'].start()

    def send_data(self, watcher, revents):
        self.watchers['timeout'].reset()
        self.server.logger.debug('Sending (%d - %d) = %d bytes to %s',
                                 self.pipe_buffer.size, watcher.data,
                                 self.pipe_buffer.size - watcher.data, self)
        watcher.data += splice(self.pipe_buffer.reader, None,
                               self.sock.fileno(), None,
                               self.pipe_buffer.size - watcher.data)[0]
        if watcher.data >= self.pipe_buffer.size:
            self.server.logger.debug('Done sending data to %s', self)
            self.stop()
        self.server.logger.debug('Sent %d bytes to %s', watcher.data, self)

    def timeout(self, watcher, revents):
        self.stop()
