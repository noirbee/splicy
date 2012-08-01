# -*- coding: utf-8 -*-

import traceback

def tb_watcher(func):
    def wrap(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception: #all other exceptions are fatal
            traceback.print_exc()
    return wrap
