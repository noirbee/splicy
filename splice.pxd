cdef extern from 'fcntl.h':

        ctypedef long long loff_t

        # Used to export constants in the .pyx file
        cdef int _SPLICE_F_MOVE "SPLICE_F_MOVE"
        cdef int _SPLICE_F_NONBLOCK "SPLICE_F_NONBLOCK"
        cdef int _SPLICE_F_MORE "SPLICE_F_MORE"
        cdef int _SPLICE_F_GIFT "SPLICE_F_GIFT"

        cdef int _F_SETPIPE_SZ "F_SETPIPE_SZ"
        cdef int _F_GETPIPE_SZ "F_GETPIPE_SZ"

        ssize_t splice(int fd_in, loff_t *off_in, int fd_out,
                       loff_t *off_out, size_t length, unsigned int flags)

        ssize_t tee(int fd_in, int fd_out, size_t length, unsigned int flags)
