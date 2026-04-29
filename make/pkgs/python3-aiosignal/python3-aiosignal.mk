$(call PKG_INIT_BIN, 1.4.0)
$(PKG)_SOURCE:=aiosignal-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=aiosignal-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/aiosignal
$(PKG)_HASH:=f47eecd9468083c2029cc99945502cb7708b082c232f9aca65da147157b251c7
### WEBSITE:=https://github.com/aio-libs/aiosignal
### CHANGES:=https://github.com/aio-libs/aiosignal/releases
### CVSREPO:=https://github.com/aio-libs/aiosignal
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-frozenlist

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiosignal/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_AIOSIGNAL, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AIOSIGNAL_DIR)/.configured
	$(RM) -r $(PYTHON3_AIOSIGNAL_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AIOSIGNAL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiosignal \
		$(PYTHON3_AIOSIGNAL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiosignal-*.dist-info

$(PKG_FINISH)
