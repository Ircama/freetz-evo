$(call PKG_INIT_BIN, 0.2.1)
$(PKG)_SOURCE:=audioop-lts-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=audioop_lts-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/audioop-lts
$(PKG)_HASH:=e81268da0baa880431b68b1308ab7257eb33f356e57a5f9b1f915dfb13dd1387
### WEBSITE:=https://github.com/AbstractUmbra/audioop
### CHANGES:=https://github.com/AbstractUmbra/audioop/releases
### CVSREPO:=https://github.com/AbstractUmbra/audioop
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/audioop/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_AUDIOOP_LTS, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AUDIOOP_LTS_DIR)/.configured
	$(RM) -r $(PYTHON3_AUDIOOP_LTS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AUDIOOP_LTS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/audioop \
		$(PYTHON3_AUDIOOP_LTS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/audioop_lts-*.dist-info

$(PKG_FINISH)
