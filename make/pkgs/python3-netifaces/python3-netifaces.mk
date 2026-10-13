$(call PKG_INIT_BIN, 0.11.0)
$(PKG)_SOURCE:=netifaces-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=netifaces-0.11.0.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/n/netifaces
$(PKG)_HASH:=043a79146eb2907edf439899f262b3dfe41717d34124298ed281139a8b93ca32
### WEBSITE:=https://pypi.org/project/netifaces/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/netifaces.cpython-$(subst .,,$(PYTHON3_MAJOR_VERSION)).so

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_NETIFACES, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_NETIFACES_DIR)/.configured
	$(RM) -r $(PYTHON3_NETIFACES_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_NETIFACES_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/netifaces.cpython-*.so

$(PKG_FINISH)
