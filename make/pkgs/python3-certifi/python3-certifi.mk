$(call PKG_INIT_BIN, 2025.10.5)
$(PKG)_SOURCE:=certifi-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=certifi-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/certifi
$(PKG)_HASH:=47c09d31ccf2acf0be3f701ea53595ee7e0b8fa08801c6624be771df09ae7b43
### WEBSITE:=https://github.com/certifi/python-certifi
### CVSREPO:=https://github.com/certifi/python-certifi
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/certifi/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_CERTIFI, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_CERTIFI_DIR)/.configured
	$(RM) -r $(PYTHON3_CERTIFI_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CERTIFI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/certifi \
		$(PYTHON3_CERTIFI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/certifi-*.dist-info

$(PKG_FINISH)
