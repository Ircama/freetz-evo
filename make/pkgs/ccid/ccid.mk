$(call PKG_INIT_BIN, 1.8.2)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=d74294e23d436546c3e719c95a4da180b17f5e7ffdd36efca53f75351cb0de75
$(PKG)_SITE:=https://ccid.apdu.fr/files
### WEBSITE:=https://ccid.apdu.fr/
### MANPAGE:=https://salsa.debian.org/rousseau/CCID/blob/master/README.md
### CHANGES:=https://salsa.debian.org/rousseau/CCID/blob/master/README.md#history
### CVSREPO:=https://salsa.debian.org/rousseau/CCID
### STEWARD:=fda77

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libccid.so
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PCSC_LITE_USBDROPDIR)/ifd-ccid.bundle/Contents/Linux/libccid.so

$(PKG)_UDEV_RULESFILE:=$($(PKG)_DIR)/src/92_pcscd_ccid.rules
$(PKG)_UDEV_TARGET_RULESFILE:=$($(PKG)_DEST_DIR)/etc/udev/rules.d/92_pcscd_ccid.rules

$(PKG)_DEPENDS_ON += meson-host
$(PKG)_DEPENDS_ON += libusb1 pcsc-lite zlib

$(PKG)_CONFIGURE_OPTIONS += -D backend=ninja
$(PKG)_CONFIGURE_OPTIONS += -D buildtype=release
$(PKG)_CONFIGURE_OPTIONS += -D debug=false
$(PKG)_CONFIGURE_OPTIONS += -D default_library=shared
$(PKG)_CONFIGURE_OPTIONS += -D embedded=true
$(PKG)_CONFIGURE_OPTIONS += -D enable-extras=false
$(PKG)_CONFIGURE_OPTIONS += -D pcsclite=true
$(PKG)_CONFIGURE_OPTIONS += -D serial=false
$(PKG)_CONFIGURE_OPTIONS += -D udev-rules=false

$(PKG)_CONFIGURE_POST_CMDS += $(call PKG_PREVENT_MESON_BUILD_RPATH,builddir/build.ninja)


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_MESON)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMESON) compile \
		-C $(CCID_DIR)/builddir/
#meson	$(MESON) configure $(HARFBUZZ_DIR)/builddir/

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(SUBMESON) install \
		--destdir "$(abspath $(CCID_DEST_DIR))" \
		-C $(CCID_DIR)/builddir/

$($(PKG)_UDEV_RULESFILE): $($(PKG)_DIR)/.configured
	@touch -c $@

$($(PKG)_UDEV_TARGET_RULESFILE): $($(PKG)_UDEV_RULESFILE)
	$(INSTALL_FILE)

$(pkg):

$(pkg)-precompiled: $(CCID_TARGET_BINARY) $(CCID_UDEV_TARGET_RULESFILE)


$(pkg)-clean:
	-$(SUBMAKE) -C $(CCID_DIR) clean
	$(RM) $(CCID_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(CCID_TARGET_BINARY) $(CCID_UDEV_TARGET_RULESFILE)

$(PKG_FINISH)
