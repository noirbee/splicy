#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.67])
AC_INIT([splicy], [0.1.0~dev], [nicolas@noirbent.fr])

AC_CONFIG_HEADERS([config.h])

AM_INIT_AUTOMAKE([foreign color-tests])

# Checks for programs.
AC_PROG_CC
AC_PROG_LIBTOOL
AM_PATH_PYTHON
AC_PYTHON_DEVEL

AC_CHECK_HEADER([fcntl.h], [], [AC_MSG_ERROR("fnctl.h not found")])
AC_CHECK_FUNCS([splice tee], [], [AC_MSG_ERROR("splice() and tee() are needed")])

AC_OUTPUT([
	Makefile
])
