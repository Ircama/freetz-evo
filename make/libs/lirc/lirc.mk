$(call PKG_INIT_LIB, 0.10.2)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=3d44ec8274881cf262f160805641f0827ffcc20ade0d85e7e6f3b90e0d3d222a
$(PKG)_SITE:=https://sourceforge.net/projects/lirc/files/LIRC/$($(PKG)_VERSION)
### WEBSITE:=https://lirc.org/
### CHANGES:=https://sourceforge.net/projects/lirc/files/LIRC/

$(PKG)_LIB_VERSION:=0.6.0
$(PKG)_BINARY:=$($(PKG)_DIR)/lib/.libs/liblirc_client.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblirc_client.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/liblirc_client.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-daemon
$(PKG)_CONFIGURE_OPTIONS += --disable-tools
$(PKG)_CONFIGURE_OPTIONS += --disable-plugins

$(PKG)_DEPENDS_ON += python3-host

$(PKG)_CONFIGURE_ENV += PYTHON="$(abspath $(TOOLS_DIR)/path/python3)"
$(PKG)_CONFIGURE_ENV += PYTHON3="$(abspath $(TOOLS_DIR)/path/python3)"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIRC_DIR)/lib

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIRC_DIR)/lib \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	# Install lirc.pc for pkg-config (meson uses dependency('lirc'))
	cp $(LIRC_DIR)/lirc.pc $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/lirc.pc
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIRC_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/liblirc_client.so*

$(PKG_FINISH)
