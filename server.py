# -*- coding: utf-8 -*-

import logging
import random
from signal import SIGHUP, SIGINT, SIGTERM
import socket

from pyev import EV_READ

from splicy.backend import Backend
from splicy.clients import InboundClient
from splicy.pipe_cache import PipeCache


class Server(object):

    BACKLOG = 1000

    def __init__(self, loop, host, port, backends):
        self.loop = loop
        self.host = host
        self.port = port
        self.clients = {}
        self.sock = None
        self.watchers = {}
        self.cache = PipeCache()
        # FIXME: configurable logging
        self.logger = logging.getLogger('splicy')
        self.backends = []
        self.create_backends(backends)

    def create_backends(self, backends):
        # FIXME: will block on DNS requests
        for host, port in backends:
            # FIXME: IPv4 only
            for address_info in socket.getaddrinfo(host, int(port),
                                                   socket.AF_INET,
                                                   socket.SOCK_STREAM,
                                                   socket.IPPROTO_TCP):
                # We're only interested in the address tuple
                backend = Backend(self, self.cache, address_info)
                self.backends.append(backend)

    def create_socket(self):
        self.sock = socket.socket(socket.AF_INET,
                                    socket.SOCK_STREAM,
                                    socket.IPPROTO_TCP)
        self.sock.setsockopt(socket.SOL_SOCKET,
                             socket.SO_REUSEADDR,
                             1)
        self.sock.setblocking(False)
        self.sock.bind((self.host, self.port))
        self.sock.listen(self.BACKLOG)
        self.watchers['accept'] = self.loop.io(self.sock.fileno(),
                                               EV_READ,
                                               self.accept_client)
        self.watchers['accept'].start()
        for signum in (SIGTERM, SIGINT,):
            self.watchers[signum] = self.loop.signal(signum, self.stop)
            self.watchers[signum].start()
        for signum in (SIGHUP,):
            self.watchers[signum] = self.loop.signal(signum, self.reload)
            self.watchers[signum].start()

    def accept_client(self, watcher, revents):
        try:
            client_socket, client_address = self.sock.accept()
            client = InboundClient(self,
                                   self.loop,
                                   client_socket,
                                   client_address)
            self.clients[client.sock] = client
            client.start()
        except:
            import traceback
            traceback.print_exc()
            raise

    def remove_client(self, client):
        if client.sock in self.clients:
            self.logger.debug('Removing client %s', client)
            self.clients.pop(client.sock)

    def select_backend(self, client, request_parser, data):
        # FIXME: make this method user-customisable
        return random.choice(self.backends)

    def proxy(self, client, request_parser, data):
        if self.cache.is_available(request_parser):
            self.cache.pipe_response(request_parser, client.pipe_buffer)
            client.start_sending()
        else:
            # Request has not yet been fetched from backend
            if not self.cache.is_processing(request_parser):
                # Initiate request through one of our backends
                backend = self.select_backend(client, request_parser, data)
                backend_request = backend.backend_request(request_parser)
                self.cache.add_processing(request_parser, backend_request)
                backend_request.start()
            self.cache.attach_processing_client(request_parser, client)

            # # FIXME: actual background request
            # self.cache.pipe_error(client.pipe_buffer)
            # client.start_sending()

    def start(self):
        self.logger.info('Serving on %s:%d', self.host, self.port)
        self.loop.start()

    def stop(self, watcher, revents):
        self.logger.info('Got signal %d, stopping.', watcher.signum)
        self.loop.stop()

    def reload(self, watcher, revents):
        self.logger.info('Got signal %d, reloading', watcher.signum)
        self.cache.clear_cache()
