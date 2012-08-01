# -*- coding: utf-8 -*-

from splicy.httpclient import HTTPClient
from splicy.pipe_buffer import PipeBuffer


class BackendRequest(HTTPClient):

    def __init__(self, backend, request_parser, loop, url, headers = None, body = b'', addr_info = None,
                 logger = None):
        HTTPClient.__init__(self, loop, url, headers, body, addr_info, logger)
        self.backend = backend
        self.request_parser = request_parser
        self.pipe_buffer = PipeBuffer()
        self.pipe_buffer_size = 0

    def on_response_headers(self, response_parser, parsed_bytes, response_buffer):
        self.logger.debug('Parsed bytes = %d, body bytes = %d', parsed_bytes, len(response_parser.body))
        header_bytes = response_buffer[:parsed_bytes]
        self.logger.debug('Headers: %s', header_bytes)
        self.pipe_buffer.write(header_bytes)
        self.pipe_buffer_size += len(header_bytes)

    def on_response_body(self, body):
        self.pipe_buffer.write(body)
        self.pipe_buffer.size = self.pipe_buffer_size + len(body)
        self.backend.server.logger.debug('Pipe buffer size: %d', self.pipe_buffer.size)

    def on_response(self, response_parser, body):
        self.backend.server.logger.info('Got response: %s, %s',
                                        response_parser, response_parser.headers)
        self.backend.publish_response(self.request_parser, response_parser, self.pipe_buffer)

class Backend(object):

    def __init__(self, server, cache, address_info):
        self.server = server
        self.cache = cache
        self.address_info = address_info
        self.socket_address = address_info[4]
        self.url = 'http://%s:%d/' % self.socket_address
        self.processing_requests = {}

    def backend_request(self, request_parser):
        # FIXME: the usual URL reconstruction shenanigans
        new_request = BackendRequest(self, request_parser,
                                     self.server.loop,
                                     self.url + request_parser.request_path,
                                     request_parser.headers,
                                     request_parser.body,
                                     self.address_info,
                                     self.server.logger)
        return new_request

    def publish_response(self, request_parser, response_parser, pipe_buffer):
        self.cache.publish_response(request_parser, response_parser, pipe_buffer)
