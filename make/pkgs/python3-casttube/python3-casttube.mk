$(call PKG_INIT_BIN, 0.2.1)
$(PKG)_SOURCE:=casttube-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=casttube-0.2.1.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/casttube
$(PKG)_HASH:=54d2af8c7949aa9c5db87fb11ef0a478a5d3e7ac6d2d2ac8dd1711e3a516fc82
### WEBSITE:=https://pypi.org/project/casttube/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-requests

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/casttube/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_CASTTUBE, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_CASTTUBE_DIR)/.configured
	$(RM) -r $(PYTHON3_CASTTUBE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CASTTUBE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/casttube \
		$(PYTHON3_CASTTUBE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/casttube-*.dist-info

$(PKG_FINISH)
