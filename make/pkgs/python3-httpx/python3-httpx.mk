$(call PKG_INIT_BIN, 0.28.1)
$(PKG)_SOURCE:=httpx-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=httpx-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/h/httpx
$(PKG)_HASH:=75e98c5f16b0f35b567856f597f06ff2270a374470a5c2392242528e3e3e42fc
### WEBSITE:=https://github.com/encode/httpx
### CVSREPO:=https://github.com/encode/httpx
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-certifi
$(PKG)_DEPENDS_ON += python3-httpcore
$(PKG)_DEPENDS_ON += python3-idna

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/httpx/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_HTTPX, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_HTTPX_DIR)/.configured
	$(RM) -r $(PYTHON3_HTTPX_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_HTTPX_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/httpx \
		$(PYTHON3_HTTPX_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/httpx-*.dist-info

$(PKG_FINISH)
