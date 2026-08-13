$(call PKG_INIT_BIN, 1.3.1)
# hidws links libwebsockets which needs libuv; libuv on GCC <= 5 / uClibc
# 0.9.x-1.0.14 (libuv 1.44.2) fails to link with "undefined reference to
# pthread_atfork" (uClibc ships pthread_atfork only as hidden static-only
# symbol). libuv 1.52.1 (uClibc 1.0.58+) no longer uses pthread_atfork.
# Gated by "depends on FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in.
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=8d8859a5cf9b1dfbca31519c6dd2656b5f3d33b0c5b1c16d8161395a71aea9ff
$(PKG)_SITE:=https://github.com/Ircama/hidws/archive/refs/tags
### WEBSITE:=https://github.com/Ircama/hidws
### CHANGES:=https://github.com/Ircama/hidws/releases
### CVSREPO:=https://github.com/Ircama/hidws

$(PKG)_CATEGORY_PKGS:=Flasher tools

$(PKG)_DEPENDS_ON += hidapi
$(PKG)_DEPENDS_ON += libwebsockets

# SSL/WSS support: hidws must be built against a libwebsockets that has SSL
# (FREETZ_LIB_libwebsockets_WITH_SSL, forced on by hidws' Config.in) so it can
# serve wss:// as well as ws:// on the same port. The openssl library is only
# linked so hidws can generate a self-signed certificate on first start.
ifeq ($(strip $(FREETZ_LIB_libwebsockets_WITH_SSL)),y)
$(PKG)_DEPENDS_ON += openssl
$(PKG)_SSL_CFLAGS := -DHIDWS_SSL
$(PKG)_SSL_LIBS := -lssl -lcrypto
endif
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libwebsockets_WITH_SSL

$(PKG)_BINARY_BUILD:=$($(PKG)_DIR)/hidws
$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/hidws

$(PKG)_BINARY_HIDLIST_BUILD:=$($(PKG)_DIR)/hid-list
$(PKG)_BINARY_HIDLIST_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/hid-list

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_HIDWS

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) $(TARGET_LDFLAGS) \
		-Wall -Wextra -O0 -std=c11 \
		-D_DEFAULT_SOURCE -D_GNU_SOURCE \
		$(HIDWS_SSL_CFLAGS) \
		$(HIDWS_DIR)/hidws.c \
		-o $@ \
		-lhidapi-libusb -lwebsockets -lpthread \
		$(HIDWS_SSL_LIBS)

# NOTE: hidws MUST be built with -O0. The reader thread is miscompiled by
# GCC -O1+ on the MIPS/uClibc toolchain (NULL-deref inside hid_read_timeout
# right after "[hid] Reader thread started"). Only -O0 is stable there.

$($(PKG)_BINARY_HIDLIST_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) $(TARGET_LDFLAGS) \
		-Wall -Wextra -Os -std=c11 \
		-D_DEFAULT_SOURCE -D_GNU_SOURCE \
		$(HIDWS_DIR)/hid-list.c \
		-o $@ \
		-lhidapi-libusb

$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY_BUILD)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_BINARY_HIDLIST_TARGET): $($(PKG)_BINARY_HIDLIST_BUILD)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_TARGET) $($(PKG)_BINARY_HIDLIST_TARGET)

$(pkg)-clean:
	$(RM) $($(PKG)_BINARY_BUILD) $($(PKG)_BINARY_HIDLIST_BUILD)

$(pkg)-uninstall:
	$(RM) $($(PKG)_BINARY_TARGET) $($(PKG)_BINARY_HIDLIST_TARGET)

$(PKG_FINISH)
