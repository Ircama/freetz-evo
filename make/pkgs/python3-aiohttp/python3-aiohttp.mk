$(call PKG_INIT_BIN, 3.13.3)
$(PKG)_SOURCE:=aiohttp-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=aiohttp-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/aiohttp
$(PKG)_HASH:=a949eee43d3782f2daae4f4a2819b2cb9b0c5d3b7f7a927067cc84dafdbb9f88
### WEBSITE:=https://github.com/aio-libs/aiohttp
### CHANGES:=https://github.com/aio-libs/aiohttp/releases
### CVSREPO:=https://github.com/aio-libs/aiohttp
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-aiohappyeyeballs
$(PKG)_DEPENDS_ON += python3-aiosignal
$(PKG)_DEPENDS_ON += python3-async-timeout
$(PKG)_DEPENDS_ON += python3-attrs
$(PKG)_DEPENDS_ON += python3-charset-normalizer
$(PKG)_DEPENDS_ON += python3-frozenlist
$(PKG)_DEPENDS_ON += python3-multidict
$(PKG)_DEPENDS_ON += python3-yarl

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_AIOHTTP, , AIOHTTP_NO_EXTENSIONS=1, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AIOHTTP_DIR)/.configured
	$(RM) -r $(PYTHON3_AIOHTTP_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AIOHTTP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp \
		$(PYTHON3_AIOHTTP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp-*.dist-info

$(PKG_FINISH)
