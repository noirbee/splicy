# -*- coding: utf-8 -*-

import os


from splice cimport splice as _splice, tee as _tee
from splice cimport _SPLICE_F_MOVE, _SPLICE_F_NONBLOCK, _SPLICE_F_MORE, _SPLICE_F_GIFT
from splice cimport _F_SETPIPE_SZ, _F_GETPIPE_SZ


cdef extern from 'errno.h':

        cdef int errno


SPLICE_F_MOVE = _SPLICE_F_MOVE
SPLICE_F_NONBLOCK = _SPLICE_F_NONBLOCK
SPLICE_F_MORE = _SPLICE_F_MORE
SPLICE_F_GIFT = _SPLICE_F_GIFT

F_SETPIPE_SZ = _F_SETPIPE_SZ
F_GETPIPE_SZ = _F_GETPIPE_SZ


def splice(fd_in, off_in, fd_out, off_out, length, flags = 0):
    """
    splice(fd_in, off_in, fd_out, off_out, length, flags = 0)

    splice() moves data between two file descriptors without copying
    between kernel address space and user address space.  It transfers
    up to len bytes of data from the file descriptor fd_in to the file
    descriptor fd_out, where one of the descriptors must refer to a
    pipe.

    If fd_in refers to a pipe, then off_in must be None.  If fd_in
    does not refer to a pipe and off_in is None, then bytes are read
    from fd_in starting from the current file offset, and the current
    file offset is adjusted appropriately.  If fd_in does not refer to
    a pipe and off_in is not None, then off_in must point to a buffer
    which specifies the starting offset from which bytes will be read
    from fd_in; in this case, the current file offset of fd_in is not
    changed. Analogous statements apply for fd_out and off_out.
    """
    cdef ssize_t ret

    cdef loff_t _off_in = 0, _off_out = 0
    cdef loff_t* _off_in_addr = &_off_in
    cdef loff_t* _off_out_addr = &_off_out

    if off_in == None:
        _off_in_addr = NULL
    if off_in == 0:
        _off_in = off_in
    if off_out == None:
        _off_out_addr = NULL
    if off_out:
        _off_out = off_out

    ret = _splice(fd_in, _off_in_addr, fd_out, _off_out_addr, length, flags)
    if ret == -1:
        global errno
        raise IOError(errno, os.strerror(errno))

    return [ret, _off_in, _off_out]

def tee(fd_in, fd_out, length, flags = 0):
    """
    tee(fd_in, fd_out, length, flags = 0)

    tee() duplicates up to len bytes of data from the pipe referred to
    by the file descriptor fd_in to the pipe referred to by the file
    descriptor fd_out. It does not consume the data that is duplicated
    from fd_in; therefore, that data can be copied by a subsequent
    splice(2).
    """
    cdef ssize_t ret

    ret = _tee(fd_in, fd_out, length, flags)
    if ret == -1:
        global errno
        raise IOError(errno, os.strerror(errno))

    return ret
