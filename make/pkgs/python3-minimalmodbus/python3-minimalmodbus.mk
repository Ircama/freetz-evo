$(call PKG_INIT_BIN, 2.1.1)
$(PKG)_SOURCE:=minimalmodbus-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=minimalmodbus-2.1.1.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/m/minimalmodbus
$(PKG)_HASH:=c3f5a56e107d537e4bb420f7e735841ab2939c8ca6fb528f5fe4124571315b64
### WEBSITE:=https://pypi.org/project/minimalmodbus/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-pyserial

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/minimalmodbus.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_MINIMALMODBUS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_MINIMALMODBUS_DIR)/.configured
	$(RM) -r $(PYTHON3_MINIMALMODBUS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_MINIMALMODBUS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/minimalmodbus.py \
		$(PYTHON3_MINIMALMODBUS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/minimalmodbus-*.dist-info

$(PKG_FINISH)
