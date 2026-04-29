$(call PKG_INIT_BIN, 82.0.1)
$(PKG)_SOURCE:=setuptools-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=setuptools-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/s/setuptools
$(PKG)_HASH:=7d872682c5d01cfde07da7bccc7b65469d3dca203318515ada1de5eda35efbf9
### WEBSITE:=https://setuptools.pypa.io/
### MANPAGE:=https://setuptools.pypa.io/en/latest/
### CHANGES:=https://setuptools.pypa.io/en/latest/history.html
### CVSREPO:=https://github.com/pypa/setuptools
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/setuptools/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_SETUPTOOLS, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_SETUPTOOLS_DIR)/.configured
	$(RM) -r $(PYTHON3_SETUPTOOLS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_SETUPTOOLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/setuptools \
		$(PYTHON3_SETUPTOOLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/setuptools-*.dist-info \
		$(PYTHON3_SETUPTOOLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pkg_resources \
		$(PYTHON3_SETUPTOOLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/_distutils_hack

$(PKG_FINISH)
