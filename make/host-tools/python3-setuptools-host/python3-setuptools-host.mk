$(call TOOLS_INIT, 84.0.0)
#
$(PKG)_SOURCE_DOWNLOAD_NAME:=setuptools-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg_short)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f4695c21257f0d9b537ec2692c941d02ee143b7cc1276941349a546573b2ef73
$(PKG)_SITE:=https://distfiles.macports.org/py-setuptools,https://files.pythonhosted.org/packages/6d/44/f5da03a8ef95d369145c5bb53050e7877c9f3d312e128605fd9504829143
### WEBSITE:=https://pypi.org/project/setuptools/
### MANPAGE:=https://setuptools.pypa.io/
### CHANGES:=https://pypi.org/project/setuptools/#history
### CVSREPO:=https://github.com/pypa/setuptools
### STEWARD:=fda77

$(PKG)_DEPENDS_ON+=python3-pip-host


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)

$($(PKG)_DIR)/.installed: $($(PKG)_DIR)/.unpacked
	$(HOST_TOOLS_DIR)/usr/bin/python3 -m pip install --no-cache-dir $(PYTHON3_SETUPTOOLS_HOST_DIR)/ $(SILENT)
	@touch $@

$(pkg)-precompiled: $($(PKG)_DIR)/.installed


$(pkg)-clean:

$(pkg)-dirclean:
	$(RM) -r $(PYTHON3_SETUPTOOLS_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) -r $(PYTHON3_HOST_SITE_PACKAGES)/setuptools/
	$(RM) -r $(PYTHON3_HOST_SITE_PACKAGES)/setuptools-*.egg-info/

$(TOOLS_FINISH)
