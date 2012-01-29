#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.68])
AC_INIT([webCrawler], [VERSION], [BUG-REPORT-ADDRESS])
AM_INIT_AUTOMAKE(webCrawler, 1.0)
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADERS([config.h])

# Checks for programs.
AC_PROG_CC

# Checks for libraries.
# FIXME: Replace `main' with a function in `-lcurl':
AC_CHECK_LIB([curl], [curl_easy_init])
# FIXME: Replace `main' with a function in `-lpcre':
AC_CHECK_LIB([pcre], [pcre_exec])
# FIXME: Replace `main' with a function in `-lsqlite3':
AC_CHECK_LIB([sqlite3], [sqlite3_open])
# FIXME: Replace `main' with a function in `-lxml2':
AC_CHECK_LIB([xml2], [xmlFreeDoc])

# Checks for header files.
AC_CHECK_HEADERS([stdlib.h string.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_REALLOC
AC_CHECK_FUNCS([memset])

AC_CONFIG_FILES([Makefile
                 src/Makefile])
AC_OUTPUT
