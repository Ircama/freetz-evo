$(call PKG_INIT_BIN, 0.2.1)
$(PKG)_SOURCE:=fnvhash-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=fnvhash-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/f/fnvhash
$(PKG)_HASH:=0c7e885f44c8f06de07f442befebc590ee9ca0cc88846681f608496284ce9cd5
### WEBSITE:=https://github.com/znerol/py-fnvhash
### CVSREPO:=https://github.com/znerol/py-fnvhash
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fnvhash/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_FNVHASH, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_FNVHASH_DIR)/.configured
	$(RM) -r $(PYTHON3_FNVHASH_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_FNVHASH_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fnvhash \
		$(PYTHON3_FNVHASH_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fnvhash-*.dist-info

$(PKG_FINISH)
