$(call PKG_INIT_BIN, 3.2.2)
$(PKG)_SOURCE:=bcrypt-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=bcrypt-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/b/bcrypt
$(PKG)_HASH:=433c410c2177057705da2a9f2cd01dd157493b2a7ac14c8593a16b3dab6b6bfb
### WEBSITE:=https://github.com/pyca/bcrypt/
### CHANGES:=https://github.com/pyca/bcrypt/releases
### CVSREPO:=https://github.com/pyca/bcrypt

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += python3-cffi
$(PKG)_DEPENDS_ON += python3-six

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bcrypt/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_BCRYPT, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_BCRYPT_DIR)/.configured
	$(RM) -r $(PYTHON3_BCRYPT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_BCRYPT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bcrypt \
		$(PYTHON3_BCRYPT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bcrypt-*.dist-info

$(PKG_FINISH)
