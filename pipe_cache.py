# -*- coding: utf-8 -*-

import os

from splicy.pipe_buffer import PipeBuffer
from splicy.splice import tee


class PipeCache(object):

    def __init__(self):
        self.processing_cache = {}
        self.available_cache = {}
        self.error = PipeBuffer()
        error_string = b'HTTP/1.1 500 Internal server error\r\nConnection: close\r\nContent-Length: 0\r\n\r\n'
        self.error.size = len(error_string)
        os.write(self.error.writer, error_string)

    def hash_func(self, request_parser):
        return request_parser.request_path

    def is_available(self, request_parser):
        return self.hash_func(request_parser) in self.available_cache

    def is_processing(self, request_parser):
        return self.hash_func(request_parser) in self.processing_cache

    def add_processing(self, request_parser, backend_request):
        self.processing_cache[self.hash_func(request_parser)] = {
            'backend_request': backend_request,
            'clients': set(),
            }

    def attach_processing_client(self, request_parser, client):
        self.processing_cache[self.hash_func(request_parser)]['clients'].add(client)

    def detach_processing_client(self, request_parser, client):
        if self.hash_func(request_parser) in self.processing_cache:
            self.processing_cache[self.hash_func(request_parser)]['clients'].discard(client)

    def clear_cache(self):
        self.available_cache = {}

    def pipe_response(self, request_parser, client_buffer):
        response_buffer = self.available_cache[self.hash_func(request_parser)]
        client_buffer.size = response_buffer.size
        return tee(response_buffer.reader,
                   client_buffer.writer,
                   response_buffer.size)

    def pipe_error(self, client_buffer):
        client_buffer.size = self.error.size
        return tee(self.error.reader,
                   client_buffer.writer,
                   self.error.size)

    def publish_response(self, request_parser, response_parser, pipe_buffer):
        processed_item = self.processing_cache.pop(self.hash_func(request_parser))
        processed_buffer = processed_item['backend_request'].pipe_buffer
        self.available_cache[self.hash_func(request_parser)] = processed_buffer
        for client in processed_item['clients']:
            self.pipe_response(request_parser, client.pipe_buffer)
            client.start_sending()
