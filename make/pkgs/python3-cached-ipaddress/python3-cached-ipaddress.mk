$(call PKG_INIT_BIN, 1.1.2)
$(PKG)_SOURCE:=cached-ipaddress-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=cached_ipaddress-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/cached-ipaddress
$(PKG)_HASH:=232f62f768a2531e3d64e661eb2e484b52954ceb8d2b04ad0d2317f52ce25108
### WEBSITE:=https://pypi.org/project/cached-ipaddress/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cached_ipaddress/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_CACHED_IPADDRESS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_CACHED_IPADDRESS_DIR)/.configured
	$(RM) -r $(PYTHON3_CACHED_IPADDRESS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CACHED_IPADDRESS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cached_ipaddress \
		$(PYTHON3_CACHED_IPADDRESS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cached_ipaddress-*.dist-info \
		$(PYTHON3_CACHED_IPADDRESS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cached-ipaddress-*.dist-info

$(PKG_FINISH)
