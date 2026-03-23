$(call PKG_INIT_BIN, 1.17.0)
$(PKG)_SOURCE:=six-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=six-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/s/six
$(PKG)_HASH:=ff70335d468e7eb6ec65b95b99d3a2836546063f63acc5171de367e834932a81
### WEBSITE:=https://github.com/benjaminp/six
### CHANGES:=https://github.com/benjaminp/six/blob/main/CHANGES
### CVSREPO:=https://github.com/benjaminp/six

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/six.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_SIX, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_SIX_DIR)/.configured
	$(RM) -r $(PYTHON3_SIX_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_SIX_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/six.py \
		$(PYTHON3_SIX_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/__pycache__/six*.pyc \
		$(PYTHON3_SIX_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/six-*.dist-info

$(PKG_FINISH)
