========
 splicy
========

splicy is an experimental splice(2) -based in-memory HTTP caching proxy server.

This is mostly a toy/proof-of-concept project, and should be viewed as
such; there is no actual backend, HTTP proxy headers or cache
management. Likewise, the performance is most likely horrendous. Use
at your own risk.


Principles of operation
=======================

splicy is an application of some of the concepts exposed by Linus
Torvalds when he gave his high-level description of the Linux-specific
``splice(2)`` and ``tee(2)`` system calls, which can be found here:
http://kerneltrap.org/node/6505

Instead of using regular ``send(2)`` / ``recv(2)`` system calls and
userspace virtual memory (such as the one obtained using ``malloc(2)``
or ``mmap(2)``) to proxy and store the cached HTTP responses from its
backends, splicy uses ``splice(2)`` / ``tee(2)`` and the kernelspace
memory provided by ``pipe(2)``. The idea is to try and achieve true
zero-copy operation, as the kernel is able to just move/duplicate data
without actually copying it.


License
=======

splicy is © 2012 Nicolas Noirbent, and is available under the
`AGPL3+ license <http://www.gnu.org/licenses/agpl-3.0.html>`_.


Build and installation
=======================

Bootstrapping
-------------

splicy uses the autotools for its build system.

If you checked out code from the git repository, you will need
autoconf and automake to generate the configure script and Makefiles.

To generate them, simply run::

    $ autoreconf -fvi

Building
--------

You will need `Cython <http://cython.org/>`_ to build the Python
binding to ``splice(2)`` and ``tee(2)``.

You need to be able to build Python extensions to build splicy. On
most distributions this means installing the ``python-dev`` or
``python-devel`` package.

splicy builds like your typical autotools-based project::

    $ ./configure && make && make install

Runtime
-------

You will need Linux >= 2.6.17, glibc >= 2.5, Python >= 2.6 and
`cyhttp11 <http://github.com/noirbee/cyhttp11>`_ to run splicy.
