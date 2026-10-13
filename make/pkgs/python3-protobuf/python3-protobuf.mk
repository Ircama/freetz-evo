$(call PKG_INIT_BIN, 7.36.2)
$(PKG)_SOURCE:=protobuf-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=protobuf-7.36.2.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/protobuf
$(PKG)_HASH:=497d0463ff3316681da6c0b9e8d06cb465d61abce00b613ab42226175644d1bb
### WEBSITE:=https://pypi.org/project/protobuf/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/google/protobuf/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_PROTOBUF, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PROTOBUF_DIR)/.configured
	$(RM) -r $(PYTHON3_PROTOBUF_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PROTOBUF_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/google/protobuf \
		$(PYTHON3_PROTOBUF_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/protobuf-*.dist-info

$(PKG_FINISH)
