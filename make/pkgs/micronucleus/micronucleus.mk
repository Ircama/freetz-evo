$(call PKG_INIT_BIN, 2.6)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=586d7bb1c064fe93dc5fc5b5ae0651641cd7fa8272b06cfd11feb6a0b2a06b9c
$(PKG)_SITE:=https://github.com/micronucleus/micronucleus/archive/refs/tags
### WEBSITE:=https://github.com/micronucleus/micronucleus
### CHANGES:=https://github.com/micronucleus/micronucleus/releases
### CVSREPO:=https://github.com/micronucleus/micronucleus

$(PKG)_CATEGORY:=Flasher tools

$(PKG)_BINARY_BUILD:=$($(PKG)_DIR)/commandline/micronucleus
$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/micronucleus

$(PKG)_DEPENDS_ON += libusb
$(PKG)_REBUILD_SUBOPTS += $(LIBUSB_REBUILD_SUBOPTS)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_BUILD): $($(PKG)_DIR)/.configured
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -Wall -Wextra -Os \
		-I$(MICRONUCLEUS_DIR)/commandline/library \
		-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include \
		$(MICRONUCLEUS_DIR)/commandline/micronucleus.c \
		$(MICRONUCLEUS_DIR)/commandline/library/micronucleus_lib.c \
		$(MICRONUCLEUS_DIR)/commandline/library/littleWire_util.c \
		-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib \
		-lusb \
		-o $@

$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY_BUILD)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARY_TARGET)

$(pkg)-clean:
	$(RM) $($(PKG)_BINARY_BUILD)

$(pkg)-uninstall:
	$(RM) $($(PKG)_BINARY_TARGET)

$(PKG_FINISH)