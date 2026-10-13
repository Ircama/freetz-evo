$(call PKG_INIT_BIN, 1.4.4)
$(PKG)_SOURCE:=appdirs-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=appdirs-1.4.4.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/appdirs
$(PKG)_HASH:=7d5d0167b2b1ba821647616af46a749d1c653740dd0d2415100fe26e27afdf41
### WEBSITE:=https://pypi.org/project/appdirs/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/appdirs.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_APPDIRS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_APPDIRS_DIR)/.configured
	$(RM) -r $(PYTHON3_APPDIRS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_APPDIRS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/appdirs.py \
		$(PYTHON3_APPDIRS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/appdirs.py-*.dist-info

$(PKG_FINISH)
