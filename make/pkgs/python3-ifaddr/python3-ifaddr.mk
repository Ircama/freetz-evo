$(call PKG_INIT_BIN, 0.2.0)
$(PKG)_SOURCE:=ifaddr-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=ifaddr-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/i/ifaddr
$(PKG)_HASH:=cc0cbfcaabf765d44595825fb96a99bb12c79716b73b44330ea38ee2b0c4aed4
### WEBSITE:=https://github.com/pydron/ifaddr
### CVSREPO:=https://github.com/pydron/ifaddr
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ifaddr/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_IFADDR, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_IFADDR_DIR)/.configured
	$(RM) -r $(PYTHON3_IFADDR_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_IFADDR_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ifaddr \
		$(PYTHON3_IFADDR_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ifaddr-*.dist-info

$(PKG_FINISH)