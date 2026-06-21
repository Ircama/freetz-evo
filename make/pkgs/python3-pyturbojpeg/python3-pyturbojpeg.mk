$(call PKG_INIT_BIN, $(if $(FREETZ_PACKAGE_PYTHON3_PYTURBOJPEG_VERSION_ABANDON),1.8.3,2.2.0))
$(PKG)_SOURCE:=pyturbojpeg-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pyturbojpeg-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pyturbojpeg
$(PKG)_HASH_ABANDON:=c131591a3990cc57f45a8b705d6261c25df913a19b1fe88de5e911dbe04a1d4
$(PKG)_HASH_CURRENT:=aaf0305aa9627ce7fdb8f592eb5e0fce804e1bd87db49900bcf78d7d5138eb88
$(PKG)_HASH:=$($(PKG)_HASH_$(if $(FREETZ_PACKAGE_PYTHON3_PYTURBOJPEG_VERSION_ABANDON),ABANDON,CURRENT))
### WEBSITE:=https://github.com/lilohuang/PyTurboJPEG
### CVSREPO:=https://github.com/lilohuang/PyTurboJPEG
### STEWARD:=Ircama

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_PYTURBOJPEG_VERSION_ABANDON

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-numpy

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/turbojpeg.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYTURBOJPEG, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYTURBOJPEG_DIR)/.configured
	$(RM) -r $(PYTHON3_PYTURBOJPEG_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYTURBOJPEG_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/turbojpeg.py \
		$(PYTHON3_PYTURBOJPEG_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyturbojpeg-*.dist-info

$(PKG_FINISH)
