$(call TOOLS_INIT, 26.2.1)
#
$(PKG)_SOURCE_DOWNLOAD_NAME:=pip-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg_short)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f6ad667e89a1fe78046c8f13232b247200f5258d7828f3f7883d660878e0813f
$(PKG)_SITE:=http://download.openpkg.org/components/cache/python-setup,https://distfiles.macports.org/py-pip,https://files.pythonhosted.org/packages/ae/15/4500e320e6b101ec3b719ae85b697d9940b6cda672bc555bd6016fc60c6f
### WEBSITE:=https://pypi.org/project/pip/
### MANPAGE:=https://pip.pypa.io/
### CHANGES:=https://pypi.org/project/pip/#history
### CVSREPO:=https://github.com/pypa/pip
### STEWARD:=fda77

$(PKG)_DEPENDS_ON+=python3-host

$(PKG)_DIRECTORY:=$($(PKG)_DIR)/src/pip


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)

$($(PKG)_DIR)/.installed: $($(PKG)_DIR)/.unpacked
	cp -fa $(PYTHON3_PIP_HOST_DIRECTORY) $(PYTHON3_HOST_SITE_PACKAGES)/
	@touch $@

$(pkg)-precompiled: $($(PKG)_DIR)/.installed


$(pkg)-clean:

$(pkg)-dirclean:
	$(RM) -r $(PYTHON3_PIP_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) -r $(PYTHON3_HOST_SITE_PACKAGES)/pip/

$(TOOLS_FINISH)
