# -*- coding: utf-8 -*-

import errno
import logging
import os
import socket
import urlparse

import pyev
import cyhttp11


class HTTPError(Exception):
    pass


class HTTPParseError(HTTPError):
    pass


class HTTPClient(object):

    REQUEST_METHOD = b'GET'
    HTTP_VERSION = b'HTTP/1.1'
    RESPONSE_MAX_SIZE = 4096
    RESPONSE_BODY_MAX_SIZE = 4 * 2**20
    RECV_BUFFER_SIZE = 64 * 2**10

    def __init__(self, loop, url, headers = None, body = b'', addr_info = None,
                 logger = None):
        self.loop = loop
        self.url = url
        self.parsed_url = urlparse.urlparse(url)
        if addr_info:
            self.sock = socket.socket(addr_info[0], addr_info[1], addr_info[2])
            self.host_address = addr_info[4][0]
            self.host_port = addr_info[4][1]
        else:
            self.sock = socket.socket()
            self.host_address = self.parsed_url.hostname
            self.host_port = self.parsed_url.port or 80

        if headers is not None:
            self.headers = headers
        else:
            self.headers = {b'Host': self.parsed_url.hostname}
        self.body = body

        self.logger = logger or logging.getLogger('httpclient')

        self.sock.setblocking(0)
        error = self.sock.connect_ex((self.host_address,
                                      self.host_port))
        if error and error != errno.EINPROGRESS:
            raise socket.error(error, os.strerror(error))

        self.watcher = self.loop.io(self.sock, pyev.EV_WRITE, self.handle_connect)

    def start(self):
        self.watcher.start()

    def on_connect(self):
        """
        Called once connection to the remote server has been
        established.
        """
        pass

    def on_request_headers(self):
        """
        Called once the HTTP headers have been fully sent to the
        server.
        """
        pass

    def on_request_body(self):
        """
        Called once the HTTP request body has been fully sent to the
        server.
        """
        pass

    def on_request(self):
        """
        Called once the HTTP request (headers and body) has been fully
        sent to the server.
        """
        pass

    def on_response_headers(self, response_parser,
                            parsed_bytes,
                            response_buffer):
        """
        Called once the HTTP response headers have been received from
        the server.
        """
        pass

    # The following method is part of the API, but is intentionally
    # commented out since its presence is checked (through hasattr())
    # to choose between streaming body chunks to the user or returning
    # the complete body at the end of the response.
    # def on_response_body_chunk(self, body_chunk):
    #     """
    #     Called every time a part of the HTTP response body is received
    #     from the server.
    #     """
    #     pass

    def on_response_body(self, body):
        """
        Called once the HTTP response body has been received from the
        server.
        """
        pass

    def on_response(self, response_parser, body):
        """
        Called once the HTTP response (headers and body) has been
        received from the server.
        """
        pass

    # Underlying implementation starts here

    def handle_connect(self, watcher, revents):
        error = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if error:
            # FIXME: on_error() ?
            raise socket.error(error, os.strerror(error))
        self.address = self.sock.getpeername()
        # Perform user-supplied callback
        self.on_connect()
        # We're connected, prepare to send our request
        self._request = memoryview(self._build_request())
        self._request_sent_bytes = 0
        watcher.callback = self.handle_headers

    @staticmethod
    def _build_http_headers(headers, body):
        default_headers = {
            b'Connection': b'close',
            b'Content-Length': len(body),
            }
        default_headers.update(headers)
        return b''.join(b'%s: %s\r\n' % (key, value) for key, value
                        in default_headers.items() if value != None)

    def _build_request(self):
        # FIXME: URL encoding/quoting for the selector parts
        # FIXME: fragments are discarded
        selector = self.parsed_url.path or b'/'
        if self.parsed_url.params:
            selector = b';'.join([selector, self.parsed_url.params])
        if self.parsed_url.query:
            selector = b'?'.join([selector, self.parsed_url.query])

        request_line = b'%s %s %s' % (self.REQUEST_METHOD,
                                      selector,
                                      self.HTTP_VERSION)
        # FIXME: should we send some more headers ?
        # FIXME: handle Basic authorisation scheme header ?
        headers_lines = self._build_http_headers(self.headers, self.body)
        # FIXME: should we send a body ?
        return b'\r\n'.join([request_line, headers_lines, b''])

    def handle_headers(self, watcher, revents):
        self._request_sent_bytes += self.sock.send(self._request[self._request_sent_bytes:])
        if self._request_sent_bytes >= len(self._request):
            # Headers sent
            self.on_request_headers()
            # Switch to sending body
            self._body_sent_bytes = 0
            watcher.callback = self.handle_body

    def handle_body(self, watcher, revents):
        self._body_sent_bytes += self.sock.send(self.body[self._body_sent_bytes:])
        if self._body_sent_bytes >= len(self.body):
            # Body sent
            self.on_request_body()
            # Full request sent
            self.on_request()
            # Switch to HTTP response handling
            self.response_buffer = b''
            self.response_parser = cyhttp11.HTTPClientParser()
            watcher.stop()
            watcher.set(self.sock, pyev.EV_READ)
            watcher.start()
            watcher.callback = self.handle_response_headers

    def handle_response_headers(self, watcher, revents):
        tmp_buffer = self.sock.recv(self.RESPONSE_MAX_SIZE -
                                    len(self.response_buffer))
        if tmp_buffer == b'':
            raise HTTPError('Unexpected end of stream from %s, %s' %
                            (self.url,
                             (self.sock, self.address)))
        self.response_buffer += tmp_buffer
        parsed_bytes = self.response_parser.execute(self.response_buffer)
        if self.response_parser.has_error():
            raise HTTPParseError('Invalid HTTP response from %s, %s' %
                                 (self.sock, self.address))
        elif self.response_parser.is_finished():
            self.on_response_headers(self.response_parser, parsed_bytes,
                                     self.response_buffer)
            if not hasattr(self, 'on_response_body_chunk'):
                self.response_body = self.response_parser.body
                watcher.callback = self.handle_response_body
            else:
                self.response_body = b''
                self.on_response_body_chunk(self.response_parser.body)
            self.watcher.callback = self.handle_response_body
        elif len(self.response_buffer) >= self.RESPONSE_MAX_SIZE:
            raise HTTPParseError('Oversized HTTP response from %s, %s' %
                                 (self.sock, self.address))

    def handle_response_body(self, watcher, revents):
        tmp_buffer = self.sock.recv(self.RESPONSE_BODY_MAX_SIZE -
                                    len(self.response_body))
        if tmp_buffer == b'':
            # End of stream
            # FIXME: Content-Length handling
            if not hasattr(self, 'on_response_body_chunk'):
                self.on_response_body(self.response_body)
                self.on_response(self.response_parser, self.response_body)
            else:
                self.on_response_body_chunk(b'')
            watcher.stop()
        else:
            if not hasattr(self, 'on_response_body_chunk'):
                if len(self.response_body) + len(tmp_buffer) >= self.RESPONSE_BODY_MAX_SIZE:
                    raise HTTPError('Oversized HTTP response body from %s, %s' %
                                    (self.sock, self.address))
                self.response_body = self.response_body + tmp_buffer
            else:
                self.on_response_body_chunk(tmp_buffer)
