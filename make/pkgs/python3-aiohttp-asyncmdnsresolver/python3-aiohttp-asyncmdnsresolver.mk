$(call PKG_INIT_BIN, 0.1.1)
$(PKG)_SOURCE:=aiohttp-asyncmdnsresolver-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=aiohttp_asyncmdnsresolver-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/aiohttp-asyncmdnsresolver
$(PKG)_HASH:=8c65d4b08b42c8a260717a2766bd5967a1d437cee852a9b21f3928b5171a7c81
### WEBSITE:=https://github.com/aio-libs/aiohttp-asyncmdnsresolver
### CVSREPO:=https://github.com/aio-libs/aiohttp-asyncmdnsresolver

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-aiohttp
$(PKG)_DEPENDS_ON += python3-aiodns
$(PKG)_DEPENDS_ON += python3-zeroconf

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp_asyncmdnsresolver/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_AIOHTTP_ASYNCMDNSRESOLVER, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AIOHTTP_ASYNCMDNSRESOLVER_DIR)/.configured
	$(RM) -r $(PYTHON3_AIOHTTP_ASYNCMDNSRESOLVER_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AIOHTTP_ASYNCMDNSRESOLVER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp_asyncmdnsresolver \
		$(PYTHON3_AIOHTTP_ASYNCMDNSRESOLVER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/aiohttp_asyncmdnsresolver-*.dist-info

$(PKG_FINISH)
