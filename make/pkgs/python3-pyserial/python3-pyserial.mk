$(call PKG_INIT_BIN, 3.5)
$(PKG)_SOURCE:=pyserial-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pyserial-3.5.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pyserial
$(PKG)_HASH:=3c77e014170dfffbd816e6ffc205e9842efb10be9f58ec16d3e8675b4925cddb
### WEBSITE:=https://pypi.org/project/pyserial/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/serial/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYSERIAL, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYSERIAL_DIR)/.configured
	$(RM) -r $(PYTHON3_PYSERIAL_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYSERIAL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/serial \
		$(PYTHON3_PYSERIAL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyserial-*.dist-info

$(PKG_FINISH)
