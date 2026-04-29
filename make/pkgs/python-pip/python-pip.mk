$(call PKG_INIT_BIN, 20.3.4)
$(PKG)_SOURCE:=python2-get-pip-$($(PKG)_VERSION).py
$(PKG)_SOURCE_DOWNLOAD_NAME:=get-pip.py
$(PKG)_SITE:=https://bootstrap.pypa.io/pip/2.7
$(PKG)_HASH:=40ee07eac6674b8d60fce2bbabc148cf0e2f1408c167683f110fd608b8d6f416
### WEBSITE:=https://pip.pypa.io/
### MANPAGE:=https://pip.pypa.io/en/stable/
### CHANGES:=https://pip.pypa.io/en/stable/news/
### CVSREPO:=https://github.com/pypa/pip
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/pip/__init__.py

define $(PKG)_CUSTOM_UNPACK
	mkdir -p $($(PKG)_DIR);
	cp -fa $(DL_DIR)/$(PYTHON_PIP_SOURCE) $($(PKG)_DIR)/get-pip.py
endef

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call HostPython2, cd $(PYTHON_PIP_DIR); , ./get-pip.py --disable-pip-version-check --no-warn-script-location --prefix=/usr --root=$(abspath $(PYTHON_PIP_DEST_DIR)) pip==$(PYTHON_PIP_VERSION))
	@rm -f $(PYTHON_PIP_DEST_DIR)/usr/bin/pip $(PYTHON_PIP_DEST_DIR)/usr/bin/pip2 $(PYTHON_PIP_DEST_DIR)/usr/bin/pip2.7
	@mkdir -p $(PYTHON_PIP_DEST_DIR)/usr/bin
	cp ./make/pkgs/python-pip/files/root/usr/bin/pip2 $(PYTHON_PIP_DEST_DIR)/usr/bin/pip2
	chmod 755 $(PYTHON_PIP_DEST_DIR)/usr/bin/pip2
	ln -sf pip2 $(PYTHON_PIP_DEST_DIR)/usr/bin/pip

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON_PIP_DIR)/.configured
	$(RM) -r $(PYTHON_PIP_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/pip \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/pip-*.dist-info \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/pip-*.egg-info \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/pkg_resources \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/pkg_resources-*.egg-info \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/setuptools \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/setuptools-*.dist-info \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/setuptools-*.egg-info \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/easy_install.py \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/wheel \
		$(PYTHON_PIP_DEST_DIR)$(PYTHON_SITE_PKG_DIR)/wheel-*.dist-info \
		$(PYTHON_PIP_DEST_DIR)/usr/bin/pip \
		$(PYTHON_PIP_DEST_DIR)/usr/bin/pip2 \
		$(PYTHON_PIP_DEST_DIR)/usr/bin/pip2.7

$(PKG_FINISH)
