$(call PKG_INIT_BIN, 3.0.3)
$(PKG)_SOURCE:=invoke-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=invoke-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/i/invoke
$(PKG)_HASH:=437b6a622223824380bfb4e64f612711a6b648c795f565efc8625af66fb57f0c
### WEBSITE:=https://www.pyinvoke.org/
### CHANGES:=https://github.com/pyinvoke/invoke/blob/main/changelog.rst
### CVSREPO:=https://github.com/pyinvoke/invoke
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/invoke/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_INVOKE, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_INVOKE_DIR)/.configured
	$(RM) -r $(PYTHON3_INVOKE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_INVOKE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/invoke \
		$(PYTHON3_INVOKE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/invoke-*.dist-info

$(PKG_FINISH)
