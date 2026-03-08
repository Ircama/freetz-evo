CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra
LDFLAGS ?= -static

all: freetz_proxy

freetz_proxy: freetz_proxy.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

clean:
	rm -f freetz_proxy

.PHONY: all clean
