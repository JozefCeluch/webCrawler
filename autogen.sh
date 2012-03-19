#!/bin/sh
echo aclocal
aclocal
echo autoheader
autoheader
echo automake
automake --add-missing --copy
echo autoconf
autoconf
