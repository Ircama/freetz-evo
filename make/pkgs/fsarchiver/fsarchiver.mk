$(call PKG_INIT_BIN, 0.8.9)
$(PKG)_CATEGORY:=Data Migration and Disaster Recovery
$(PKG)_SOURCE:=fsarchiver-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ade1d9d3c7de815c0b40b54e24e39b53d4a3b0add69d47f23b36fc2fd8f21843
$(PKG)_SITE:=https://github.com/fdupoux/fsarchiver/releases/download/$($(PKG)_VERSION)
### WEBSITE:=https://www.fsarchiver.org/
### MANPAGE:=https://www.fsarchiver.org/
### CHANGES:=https://github.com/fdupoux/fsarchiver/releases
### CVSREPO:=https://github.com/fdupoux/fsarchiver
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/src/fsarchiver
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/sbin/fsarchiver

$(PKG)_DEPENDS_ON += e2fsprogs parted

$(PKG)_CONFIGURE_ENV += BLKID_CFLAGS="-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/blkid"
$(PKG)_CONFIGURE_ENV += BLKID_LIBS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -lblkid -luuid"

$(PKG)_CONFIGURE_OPTIONS += --disable-lzma
$(PKG)_CONFIGURE_OPTIONS += --disable-lzo
$(PKG)_CONFIGURE_OPTIONS += --disable-lz4
$(PKG)_CONFIGURE_OPTIONS += --disable-zstd

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(FSARCHIVER_DIR) V=1 all

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	@if [ -f "$(FSARCHIVER_DIR)/Makefile" ]; then \
		$(SUBMAKE) -C $(FSARCHIVER_DIR) clean; \
	fi

$(pkg)-uninstall:
	$(RM) $(FSARCHIVER_TARGET_BINARY)

$(PKG_FINISH)
