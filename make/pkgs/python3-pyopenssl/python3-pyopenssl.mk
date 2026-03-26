$(call PKG_INIT_BIN, 26.0.0)
$(PKG)_SOURCE:=pyopenssl-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pyopenssl-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pyopenssl
$(PKG)_HASH:=f293934e52936f2e3413b89c6ce36df66a0b34ae1ea3a053b8c5020ff2f513fc
### WEBSITE:=https://github.com/pyca/pyopenssl
### CVSREPO:=https://github.com/pyca/pyopenssl

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-cryptography

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/OpenSSL/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYOPENSSL, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYOPENSSL_DIR)/.configured
	$(RM) -r $(PYTHON3_PYOPENSSL_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYOPENSSL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/OpenSSL \
		$(PYTHON3_PYOPENSSL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyopenssl-*.dist-info

$(PKG_FINISH)
