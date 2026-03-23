$(call PKG_INIT_BIN, 26.1.0)
$(PKG)_SOURCE:=attrs-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=attrs-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/attrs
$(PKG)_HASH:=d03ceb89cb322a8fd706d4fb91940737b6642aa36998fe130a9bc96c985eff32
### WEBSITE:=https://www.attrs.org/
### MANPAGE:=https://www.attrs.org/en/stable/
### CHANGES:=https://github.com/python-attrs/attrs/blob/main/CHANGELOG.md
### CVSREPO:=https://github.com/python-attrs/attrs

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/attrs/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_ATTRS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_ATTRS_DIR)/.configured
	$(RM) -r $(PYTHON3_ATTRS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ATTRS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/attrs \
		$(PYTHON3_ATTRS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/attr \
		$(PYTHON3_ATTRS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/attrs-*.dist-info

$(PKG_FINISH)
