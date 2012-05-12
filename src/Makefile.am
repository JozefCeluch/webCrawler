bin_PROGRAMS = webCrawler

CC = gcc
AM_CFLAGS = -g3 -Wall `curl-config --cflags` `xml2-config --cflags`
AM_LDFLAGS = `xml2-config --libs` `curl-config --libs` -lcurl -lsqlite3 -lpcre
webCrawler_SOURCES = main.c database.h database.c network.h network.c parse.h parse.c

