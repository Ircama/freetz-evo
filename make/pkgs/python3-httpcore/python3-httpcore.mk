$(call PKG_INIT_BIN, 1.0.9)
$(PKG)_SOURCE:=httpcore-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=httpcore-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/h/httpcore
$(PKG)_HASH:=6e34463af53fd2ab5d807f399a9b45ea31c3dfa2276f15a2c3f00afff6e176e8
### WEBSITE:=https://github.com/encode/httpcore
### CVSREPO:=https://github.com/encode/httpcore
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-certifi
$(PKG)_DEPENDS_ON += python3-h11

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/httpcore/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_HTTPCORE, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_HTTPCORE_DIR)/.configured
	$(RM) -r $(PYTHON3_HTTPCORE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_HTTPCORE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/httpcore \
		$(PYTHON3_HTTPCORE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/httpcore-*.dist-info

$(PKG_FINISH)
