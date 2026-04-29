$(call PKG_INIT_BIN, 3.4.6)
$(PKG)_SOURCE:=charset-normalizer-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=charset_normalizer-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/charset-normalizer
$(PKG)_HASH:=1ae6b62897110aa7c79ea2f5dd38d1abca6db663687c0b1ad9aed6f6bae3d9d6
### WEBSITE:=https://github.com/jawah/charset_normalizer
### CHANGES:=https://github.com/jawah/charset_normalizer/releases
### CVSREPO:=https://github.com/jawah/charset_normalizer
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/charset_normalizer/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_CHARSET_NORMALIZER, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_CHARSET_NORMALIZER_DIR)/.configured
	$(RM) -r $(PYTHON3_CHARSET_NORMALIZER_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CHARSET_NORMALIZER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/charset_normalizer \
		$(PYTHON3_CHARSET_NORMALIZER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/charset_normalizer-*.dist-info

$(PKG_FINISH)
