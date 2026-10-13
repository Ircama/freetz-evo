$(call PKG_INIT_BIN, 4.70.1)
$(PKG)_SOURCE:=tqdm-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=tqdm-4.70.1.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/t/tqdm
$(PKG)_HASH:=cefd0eca11b2a37a3aee776544d4f4ae913f02688135b5556b8788dfa474afc4
### WEBSITE:=https://pypi.org/project/tqdm/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/tqdm/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_TQDM, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_TQDM_DIR)/.configured
	$(RM) -r $(PYTHON3_TQDM_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_TQDM_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/tqdm \
		$(PYTHON3_TQDM_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/tqdm-*.dist-info

$(PKG_FINISH)
