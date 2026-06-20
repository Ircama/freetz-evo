$(call PKG_INIT_BIN, 6.8.3)
$(PKG)_SOURCE:=habluetooth-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=habluetooth-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/h/habluetooth
$(PKG)_HASH:=e2bc83250683fce51ab9c7e4f24e680d0e63ddcf946509218893f0c5e194ab52
### WEBSITE:=https://github.com/bluetooth-devices/habluetooth
### CHANGES:=https://github.com/bluetooth-devices/habluetooth/releases
### CVSREPO:=https://github.com/bluetooth-devices/habluetooth
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-bluetooth-data-tools
$(PKG)_DEPENDS_ON += python3-dbus-fast

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/habluetooth/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_HABLUETOOTH, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_HABLUETOOTH_DIR)/.configured
	$(RM) -r $(PYTHON3_HABLUETOOTH_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_HABLUETOOTH_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/habluetooth \
		$(PYTHON3_HABLUETOOTH_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/habluetooth-*.dist-info

$(PKG_FINISH)
