$(call PKG_INIT_BIN, 3.5.6)
$(PKG)_SOURCE:=greenlet-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=greenlet-3.5.6.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/g/greenlet
$(PKG)_HASH:=8e67c43bdfc88d5fee6db0d3e40175b362fc95fb85f0412d233b9b203c53a575
### WEBSITE:=https://pypi.org/project/greenlet/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/greenlet/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_GREENLET, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_GREENLET_DIR)/.configured
	$(RM) -r $(PYTHON3_GREENLET_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_GREENLET_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/greenlet \
		$(PYTHON3_GREENLET_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/greenlet-*.dist-info

$(PKG_FINISH)
