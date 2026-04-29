$(call PKG_INIT_BIN, 1.23.0)
$(PKG)_SOURCE:=yarl-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=yarl-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/y/yarl
$(PKG)_HASH:=53b1ea6ca88ebd4420379c330aea57e258408dd0df9af0992e5de2078dc9f5d5
### WEBSITE:=https://github.com/aio-libs/yarl
### CHANGES:=https://github.com/aio-libs/yarl/releases
### CVSREPO:=https://github.com/aio-libs/yarl
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-idna
$(PKG)_DEPENDS_ON += python3-multidict
$(PKG)_DEPENDS_ON += python3-propcache

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/yarl/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_YARL, , YARL_NO_EXTENSIONS=1, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_YARL_DIR)/.configured
	$(RM) -r $(PYTHON3_YARL_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_YARL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/yarl \
		$(PYTHON3_YARL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/yarl-*.dist-info

$(PKG_FINISH)
