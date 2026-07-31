$(call PKG_INIT_BIN, 1.2.2)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b4a3cd4da25535f373d400c6eb79602192a0a9c34db3df439d8fe265321f2e5e
$(PKG)_SITE:=https://github.com/Ircama/hidws/archive/refs/tags
### WEBSITE:=https://github.com/Ircama/hidws
### CHANGES:=https://github.com/Ircama/hidws/releases
### CVSREPO:=https://github.com/Ircama/hidws

$(PKG)_CATEGORY:=Flasher tools

$(PKG)_DEPENDS_ON += hidapi
$(PKG)_DEPENDS_ON += libwebsockets

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
		$(HIDWS_DIR)/hidws.c \
		-o $@ \
		-lhidapi-libusb -lwebsockets -lpthread

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
