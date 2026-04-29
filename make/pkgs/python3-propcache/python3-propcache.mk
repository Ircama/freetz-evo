$(call PKG_INIT_BIN, 0.4.1)
$(PKG)_SOURCE:=propcache-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=propcache-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/propcache
$(PKG)_HASH:=f48107a8c637e80362555f37ecf49abe20370e557cc4ab374f04ec4423c97c3d
### WEBSITE:=https://github.com/aio-libs/propcache
### CHANGES:=https://github.com/aio-libs/propcache/releases
### CVSREPO:=https://github.com/aio-libs/propcache
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/propcache/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PROPCACHE, \
		--config-settings=pure-python=true, \
		PROPCACHE_NO_EXTENSIONS=1 \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PROPCACHE_DIR)/.configured
	$(RM) -r $(PYTHON3_PROPCACHE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PROPCACHE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/propcache \
		$(PYTHON3_PROPCACHE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/propcache-*.dist-info

$(PKG_FINISH)
