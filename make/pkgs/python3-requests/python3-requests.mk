$(call PKG_INIT_BIN, 2.34.2)
$(PKG)_SOURCE:=requests-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=requests-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/r/requests
$(PKG)_HASH:=f288924cae4e29463698d6d60bc6a4da69c89185ad1e0bcc4104f584e960b9ed
### WEBSITE:=https://requests.readthedocs.io/
### CHANGES:=https://github.com/psf/requests/releases
### CVSREPO:=https://github.com/psf/requests
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-certifi
$(PKG)_DEPENDS_ON += python3-charset-normalizer
$(PKG)_DEPENDS_ON += python3-idna
$(PKG)_DEPENDS_ON += python3-urllib3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/requests/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_REQUESTS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_REQUESTS_DIR)/.configured
	$(RM) -r $(PYTHON3_REQUESTS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_REQUESTS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/requests \
		$(PYTHON3_REQUESTS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/requests-*.dist-info

$(PKG_FINISH)
