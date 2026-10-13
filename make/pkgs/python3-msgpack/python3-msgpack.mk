$(call PKG_INIT_BIN, 1.2.3)
$(PKG)_SOURCE:=msgpack-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=msgpack-1.2.3.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/m/msgpack
$(PKG)_HASH:=32edb81a2b5eb7cd7c9d941b2bfbbb082fd2cd09e0e725930316af6b708db186
### WEBSITE:=https://pypi.org/project/msgpack/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/msgpack/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_MSGPACK, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_MSGPACK_DIR)/.configured
	$(RM) -r $(PYTHON3_MSGPACK_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_MSGPACK_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/msgpack \
		$(PYTHON3_MSGPACK_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/msgpack-*.dist-info

$(PKG_FINISH)
