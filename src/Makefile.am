bin_PROGRAMS = webCrawler

CC = gcc
AM_CFLAGS = -g3 -Wall `curl-config --cflags`
AM_LDFLAGS = `curl-config --libs` -lcurl -lsqlite3 -lpcre -lxml2
webCrawler_SOURCES = main.c database.h database.c network.h network.c parse.h parse.c

