dist_bin_SCRIPTS = splicy

pkgpyexec_PYTHON = \
	__init__.py \
	backend.py \
	clients.py \
	helpers.py \
	httpclient.py \
	pipe_buffer.py \
	pipe_cache.py \
	server.py

pkgpyexec_LTLIBRARIES = splice.la
splice_la_CPPFLAGS = ${AM_CPPFLAGS} ${PYTHON_CPPFLAGS}
splice_la_CFLAGS = ${AM_CFLAGS} -fno-strict-aliasing
splice_la_LDFLAGS = ${PYTHON_LDFLAGS} -avoid-version -module

splice_la_SOURCES = splice.c

EXTRA_DIST = splice.pyx splice.pxd

splice.c: %.c: Makefile.in %.pyx %.pxd
	cython --verbose $(top_srcdir)/$*.pyx -o $@
