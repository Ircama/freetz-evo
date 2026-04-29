$(call PKG_INIT_BIN, 0.3.0)
$(PKG)_SOURCE:=aiohttp-fast-zlib-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=aiohttp_fast_zlib-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/aiohttp-fast-zlib
$(PKG)_HASH:=963a09de571b67fa0ef9cb44c5a32ede5cb1a51bc79fc21181b1cddd56b58b28
### WEBSITE:=https://github.com/bluetooth-devices/aiohttp-fast-zlib
### CVSREPO:=https://github.com/bluetooth-devices/aiohttp-fast-zlib
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-aiohttp

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp_fast_zlib/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_AIOHTTP_FAST_ZLIB, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AIOHTTP_FAST_ZLIB_DIR)/.configured
	$(RM) -r $(PYTHON3_AIOHTTP_FAST_ZLIB_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AIOHTTP_FAST_ZLIB_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp_fast_zlib \
		$(PYTHON3_AIOHTTP_FAST_ZLIB_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp_fast_zlib-*.dist-info

$(PKG_FINISH)
