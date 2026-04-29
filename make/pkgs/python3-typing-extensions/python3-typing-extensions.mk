$(call PKG_INIT_BIN, 4.15.0)
$(PKG)_SOURCE:=typing-extensions-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=typing_extensions-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/t/typing-extensions
$(PKG)_HASH:=0cea48d173cc12fa28ecabc3b837ea3cf6f38c6d1136f85cbaaf598984861466
### WEBSITE:=https://github.com/python/typing_extensions
### CVSREPO:=https://github.com/python/typing_extensions
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/typing_extensions.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_TYPING_EXTENSIONS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_TYPING_EXTENSIONS_DIR)/.configured
	$(RM) -r $(PYTHON3_TYPING_EXTENSIONS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_TYPING_EXTENSIONS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/typing_extensions.py \
		$(PYTHON3_TYPING_EXTENSIONS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/typing_extensions-*.dist-info

$(PKG_FINISH)