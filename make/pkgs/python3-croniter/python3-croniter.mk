$(call PKG_INIT_BIN, 6.2.4)
$(PKG)_SOURCE:=croniter-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=croniter-6.2.4.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/croniter
$(PKG)_HASH:=fc124f751b1b04805c2a04b061898b436b45ab2320b045e1e052ea895de65189
### WEBSITE:=https://pypi.org/project/croniter/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-dateutil

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/croniter/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_CRONITER, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_CRONITER_DIR)/.configured
	$(RM) -r $(PYTHON3_CRONITER_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CRONITER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/croniter \
		$(PYTHON3_CRONITER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/croniter-*.dist-info

$(PKG_FINISH)
