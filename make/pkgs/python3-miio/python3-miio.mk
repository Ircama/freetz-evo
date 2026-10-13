$(call PKG_INIT_BIN, 0.5.12)
$(PKG)_SOURCE:=python-miio-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=python-miio-0.5.12.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/python-miio
$(PKG)_HASH:=049c351a0dc53b647a5962a392ba710cde1f4cc4ee8390088f448dab58046c16
### WEBSITE:=https://pypi.org/project/python-miio/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-android-backup
$(PKG)_DEPENDS_ON += python3-appdirs
$(PKG)_DEPENDS_ON += python3-attrs
$(PKG)_DEPENDS_ON += python3-click
$(PKG)_DEPENDS_ON += python3-construct
$(PKG)_DEPENDS_ON += python3-croniter
$(PKG)_DEPENDS_ON += python3-cryptography
$(PKG)_DEPENDS_ON += python3-defusedxml
$(PKG)_DEPENDS_ON += python3-micloud
$(PKG)_DEPENDS_ON += python3-netifaces
$(PKG)_DEPENDS_ON += python3-pytz
$(PKG)_DEPENDS_ON += python3-pyyaml
$(PKG)_DEPENDS_ON += python3-tqdm
$(PKG)_DEPENDS_ON += python3-zeroconf

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/miio/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_MIIO, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_MIIO_DIR)/.configured
	$(RM) -r $(PYTHON3_MIIO_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_MIIO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/miio \
		$(PYTHON3_MIIO_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/miio-*.dist-info

$(PKG_FINISH)
