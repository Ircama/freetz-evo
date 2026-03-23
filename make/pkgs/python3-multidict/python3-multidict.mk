$(call PKG_INIT_BIN, 6.7.1)
$(PKG)_SOURCE:=multidict-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=multidict-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/m/multidict
$(PKG)_HASH:=ec6652a1bee61c53a3e5776b6049172c53b6aaba34f18c9ad04f82712bac623d
### WEBSITE:=https://github.com/aio-libs/multidict
### CHANGES:=https://github.com/aio-libs/multidict/releases
### CVSREPO:=https://github.com/aio-libs/multidict

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/multidict/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_MULTIDICT, , MULTIDICT_NO_EXTENSIONS=1, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_MULTIDICT_DIR)/.configured
	$(RM) -r $(PYTHON3_MULTIDICT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_MULTIDICT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/multidict \
		$(PYTHON3_MULTIDICT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/multidict-*.dist-info

$(PKG_FINISH)
