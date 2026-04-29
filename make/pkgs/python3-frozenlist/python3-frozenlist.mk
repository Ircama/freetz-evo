$(call PKG_INIT_BIN, 1.8.0)
$(PKG)_SOURCE:=frozenlist-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=frozenlist-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/f/frozenlist
$(PKG)_HASH:=3ede829ed8d842f6cd48fc7081d7a41001a56f1f38603f9d49bf3020d59a31ad
### WEBSITE:=https://github.com/aio-libs/frozenlist
### CHANGES:=https://github.com/aio-libs/frozenlist/releases
### CVSREPO:=https://github.com/aio-libs/frozenlist
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/frozenlist/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_FROZENLIST, , FROZENLIST_NO_EXTENSIONS=1, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_FROZENLIST_DIR)/.configured
	$(RM) -r $(PYTHON3_FROZENLIST_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_FROZENLIST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/frozenlist \
		$(PYTHON3_FROZENLIST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/frozenlist-*.dist-info

$(PKG_FINISH)
