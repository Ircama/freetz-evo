$(call PKG_INIT_BIN, 5.0.1)
$(PKG)_SOURCE:=async-timeout-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=async_timeout-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/async-timeout
$(PKG)_HASH:=d9321a7a3d5a6a5e187e824d2fa0793ce379a202935782d555d6e9d2735677d3
### WEBSITE:=https://github.com/aio-libs/async-timeout
### CHANGES:=https://github.com/aio-libs/async-timeout/blob/master/CHANGES.rst
### CVSREPO:=https://github.com/aio-libs/async-timeout
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/async_timeout/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_ASYNC_TIMEOUT, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_ASYNC_TIMEOUT_DIR)/.configured
	$(RM) -r $(PYTHON3_ASYNC_TIMEOUT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ASYNC_TIMEOUT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/async_timeout \
		$(PYTHON3_ASYNC_TIMEOUT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/async_timeout-*.dist-info

$(PKG_FINISH)
