$(call PKG_INIT_BIN, 26.0.1)
$(PKG)_SOURCE:=pip-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pip-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pip
$(PKG)_HASH:=c4037d8a277c89b320abe636d59f91e6d0922d08a05b60e85e53b296613346d8
### WEBSITE:=https://pip.pypa.io/
### MANPAGE:=https://pip.pypa.io/en/stable/
### CHANGES:=https://pip.pypa.io/en/stable/news/
### CVSREPO:=https://github.com/pypa/pip

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pip/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --upgrade --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) "flit-core>=3.11,<4"
	$(call Build/PyMod3/Pip, PYTHON3_PIP, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PIP_DIR)/.configured
	$(RM) -r $(PYTHON3_PIP_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PIP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pip \
		$(PYTHON3_PIP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pip-*.dist-info \
		$(PYTHON3_PIP_DEST_DIR)/usr/bin/pip* \
		$(PYTHON3_PIP_DEST_DIR)/usr/bin/pip3*

$(PKG_FINISH)
