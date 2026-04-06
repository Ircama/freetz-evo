$(call PKG_INIT_BIN, 2.3.3)
$(PKG)_SOURCE:=ciso8601-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=ciso8601-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/ciso8601
$(PKG)_HASH:=db5d78d9fb0de8686fbad1c1c2d168ed52efb6e8bf8774ae26226e5034a46dae
### WEBSITE:=https://github.com/closeio/ciso8601
### CHANGES:=https://github.com/closeio/ciso8601/releases
### CVSREPO:=https://github.com/closeio/ciso8601

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ciso8601.cpython-$(subst .,,$(PYTHON3_MAJOR_VERSION)).so

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_CISO8601, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_CISO8601_DIR)/.configured
	$(RM) -r $(PYTHON3_CISO8601_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CISO8601_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ciso8601*.so \
		$(PYTHON3_CISO8601_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ciso8601-*.dist-info

$(PKG_FINISH)
