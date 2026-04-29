$(call PKG_INIT_BIN, 1.4.1)
$(PKG)_SOURCE:=lru-dict-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=lru_dict-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/l/lru-dict
$(PKG)_HASH:=cc518ff2d38cc7a8ab56f9a6ae557f91e2e1524b57ed8e598e97f45a2bd708fc
### WEBSITE:=https://github.com/amitdev/lru-dict
### CHANGES:=https://github.com/amitdev/lru-dict/releases
### CVSREPO:=https://github.com/amitdev/lru-dict
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/lru/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_LRU_DICT, , \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_LRU_DICT_DIR)/.configured
	$(RM) -r $(PYTHON3_LRU_DICT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_LRU_DICT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/lru \
		$(PYTHON3_LRU_DICT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/lru_dict-*.dist-info

$(PKG_FINISH)
