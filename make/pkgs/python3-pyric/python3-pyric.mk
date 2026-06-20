$(call PKG_INIT_BIN, 0.1.6.3)
$(PKG)_SOURCE:=PyRIC-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=PyRIC-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/P/PyRIC
$(PKG)_HASH:=b539b01cafebd2406c00097f94525ea0f8ecd1dd92f7731f43eac0ef16c2ccc9
### WEBSITE:=http://wraith-wireless.github.io/PyRIC/
### CVSREPO:=https://github.com/wraith-wireless/pyric
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyric/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYRIC, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYRIC_DIR)/.configured
	$(RM) -r $(PYTHON3_PYRIC_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYRIC_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyric \
		$(PYTHON3_PYRIC_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/PyRIC-*.dist-info

$(PKG_FINISH)
