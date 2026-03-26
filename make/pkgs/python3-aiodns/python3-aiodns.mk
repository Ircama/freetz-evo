$(call PKG_INIT_BIN, 4.0.0)
$(PKG)_SOURCE:=aiodns-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=aiodns-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/aiodns
$(PKG)_HASH:=17be26a936ba788c849ba5fd20e0ba69d8c46e6273e846eb5430eae2630ce5b1
### WEBSITE:=https://github.com/saghul/aiodns
### CHANGES:=https://github.com/saghul/aiodns/releases
### CVSREPO:=https://github.com/saghul/aiodns

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-pycares

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiodns/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_AIODNS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AIODNS_DIR)/.configured
	$(RM) -r $(PYTHON3_AIODNS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AIODNS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiodns \
		$(PYTHON3_AIODNS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiodns-*.dist-info

$(PKG_FINISH)
