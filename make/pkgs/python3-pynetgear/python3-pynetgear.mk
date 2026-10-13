$(call PKG_INIT_BIN, 0.10.10)
$(PKG)_SOURCE:=pynetgear-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pynetgear-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pynetgear
$(PKG)_HASH:=35f8d3bfa4e876466c7a9e99a6cd621d974e681efc0e85211be9dc216c1e3b84
### WEBSITE:=https://pypi.org/project/pynetgear/
### CVSREPO:=https://github.com/MatMaul/pynetgear
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-requests

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pynetgear/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# The sdist of pynetgear 0.10.10 does not ship requirements.txt, although its
# setup.py reads it while pip asks setuptools for the build requirements, so the
# build stops with "FileNotFoundError: 'requirements.txt'". Create the file as
# the upstream repository has it (requests is provided by python3-requests, and
# pip is called with --no-deps).
$($(PKG)_DIR)/requirements.txt: $($(PKG)_DIR)/.unpacked
	printf 'requests>=2.0\n' > $@

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/requirements.txt $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYNETGEAR, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYNETGEAR_DIR)/.configured
	$(RM) -r $(PYTHON3_PYNETGEAR_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYNETGEAR_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pynetgear \
		$(PYTHON3_PYNETGEAR_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pynetgear-*.dist-info

$(PKG_FINISH)
