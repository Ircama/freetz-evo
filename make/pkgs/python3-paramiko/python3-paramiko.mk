$(call PKG_INIT_BIN, 5.0.0)
$(PKG)_SOURCE:=paramiko-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=paramiko-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/paramiko
$(PKG)_HASH:=36763b5b95c2a0dcfdf1abc48e48156ee425b21efe2f0e787c2dd5a95c0e5e79
### WEBSITE:=https://www.paramiko.org/
### CHANGES:=https://www.paramiko.org/changelog.html
### CVSREPO:=https://github.com/paramiko/paramiko
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-bcrypt
$(PKG)_DEPENDS_ON += python3-cryptography
$(PKG)_DEPENDS_ON += python3-invoke
$(PKG)_DEPENDS_ON += python3-pynacl

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/paramiko/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PARAMIKO, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PARAMIKO_DIR)/.configured
	$(RM) -r $(PYTHON3_PARAMIKO_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PARAMIKO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/paramiko \
		$(PYTHON3_PARAMIKO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/paramiko-*.dist-info

$(PKG_FINISH)
