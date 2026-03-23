$(call PKG_INIT_BIN, 2.6.1)
$(PKG)_SOURCE:=aiohappyeyeballs-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=aiohappyeyeballs-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/aiohappyeyeballs
$(PKG)_HASH:=c3f9d0113123803ccadfdf3f0faa505bc78e6a72d1cc4806cbd719826e943558
### WEBSITE:=https://github.com/aio-libs/aiohappyeyeballs
### CHANGES:=https://github.com/aio-libs/aiohappyeyeballs/releases
### CVSREPO:=https://github.com/aio-libs/aiohappyeyeballs

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohappyeyeballs/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_AIOHAPPYEYEBALLS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AIOHAPPYEYEBALLS_DIR)/.configured
	$(RM) -r $(PYTHON3_AIOHAPPYEYEBALLS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AIOHAPPYEYEBALLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohappyeyeballs \
		$(PYTHON3_AIOHAPPYEYEBALLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohappyeyeballs-*.dist-info

$(PKG_FINISH)
