$(call PKG_INIT_BIN, 3.17)
$(PKG)_SOURCE:=mashumaro-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=mashumaro-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/m/mashumaro
$(PKG)_HASH:=de1d8b1faffee58969c7f97e35963a92480a38d4c9858e92e0721efec12258ed
### WEBSITE:=https://github.com/Fatal1ty/mashumaro
### CVSREPO:=https://github.com/Fatal1ty/mashumaro

$(PKG)_DEPENDS_ON += python3 python3-typing-extensions

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/mashumaro/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_MASHUMARO, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_MASHUMARO_DIR)/.configured
	$(RM) -r $(PYTHON3_MASHUMARO_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_MASHUMARO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/mashumaro \
		$(PYTHON3_MASHUMARO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/mashumaro-*.dist-info

$(PKG_FINISH)