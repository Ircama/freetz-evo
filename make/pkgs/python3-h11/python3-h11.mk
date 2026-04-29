$(call PKG_INIT_BIN, 0.16.0)
$(PKG)_SOURCE:=h11-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=h11-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/h/h11
$(PKG)_HASH:=4e35b956cf45792e4caa5885e69fba00bdbc6ffafbfa020300e549b208ee5ff1
### WEBSITE:=https://github.com/python-hyper/h11
### CVSREPO:=https://github.com/python-hyper/h11
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/h11/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_H11, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_H11_DIR)/.configured
	$(RM) -r $(PYTHON3_H11_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_H11_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/h11 \
		$(PYTHON3_H11_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/h11-*.dist-info

$(PKG_FINISH)
