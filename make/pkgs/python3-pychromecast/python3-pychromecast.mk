$(call PKG_INIT_BIN, 14.0.10)
$(PKG)_SOURCE:=pychromecast-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pychromecast-14.0.10.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pychromecast
$(PKG)_HASH:=f05a1c8d727d4f104c8c731688053033e05157f2ab81bc8eef50ec0c62f9373c
### WEBSITE:=https://pypi.org/project/pychromecast/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-protobuf
$(PKG)_DEPENDS_ON += python3-casttube
$(PKG)_DEPENDS_ON += python3-zeroconf

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pychromecast/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYCHROMECAST, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYCHROMECAST_DIR)/.configured
	$(RM) -r $(PYTHON3_PYCHROMECAST_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYCHROMECAST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pychromecast \
		$(PYTHON3_PYCHROMECAST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pychromecast-*.dist-info

$(PKG_FINISH)
