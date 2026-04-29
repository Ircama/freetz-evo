$(call PKG_INIT_BIN, 1.0.2)
$(PKG)_SOURCE:=annotatedyaml-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=annotatedyaml-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/annotatedyaml
$(PKG)_HASH:=f9a49952994ef1952ca17d27bb6478342eb1189d2c28e4c0ddbbb32065471fb0
### WEBSITE:=https://github.com/home-assistant-libs/annotatedyaml
### CHANGES:=https://github.com/home-assistant-libs/annotatedyaml/releases
### CVSREPO:=https://github.com/home-assistant-libs/annotatedyaml
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += python3-propcache
$(PKG)_DEPENDS_ON += python3-pyyaml
$(PKG)_DEPENDS_ON += python3-voluptuous

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/annotatedyaml/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Build with optional Cython C extension for performance.
# The build_ext.py gracefully falls back to pure Python if Cython is unavailable.
$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) Cython==3.2.0 $(SILENT)
	$(call Build/PyMod3/PKG, PYTHON3_ANNOTATEDYAML, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_ANNOTATEDYAML_DIR)/.configured
	$(RM) -r $(PYTHON3_ANNOTATEDYAML_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ANNOTATEDYAML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/annotatedyaml \
		$(PYTHON3_ANNOTATEDYAML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/annotatedyaml-*.dist-info

$(PKG_FINISH)
