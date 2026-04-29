$(call PKG_INIT_BIN, 6.0.3)
$(PKG)_SOURCE:=pyyaml-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pyyaml-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pyyaml
$(PKG)_HASH:=d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f
### WEBSITE:=https://pyyaml.org/
### MANPAGE:=https://pyyaml.org/wiki/PyYAMLDocumentation
### CHANGES:=https://github.com/yaml/pyyaml/blob/main/CHANGES
### CVSREPO:=https://github.com/yaml/pyyaml
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += yaml

# Build mode selector:
# - default (y): build with LibYAML C extension
# - set to n: force pure-Python fallback
# Example:
#   make PYTHON3_PYYAML_USE_C=n python3-pyyaml-precompiled
PYTHON3_PYYAML_USE_C ?= y

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/yaml/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
ifeq ($(PYTHON3_PYYAML_USE_C),y)
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) Cython==3.2.0 $(SILENT)
	$(call Build/PyMod3/PKG, PYTHON3_PYYAML, , \
		PYYAML_FORCE_LIBYAML=1 \
		PYYAML_FORCE_CYTHON=1 \
	)
	find $(PYTHON3_PYYAML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR) -type f -name "*.cpython-*-*-linux-gnu.so" | while read -r so; do \
		new_so="$$(echo "$$so" | sed -E 's/\.cpython-([0-9]+)-[^/]*\.so$$/.cpython-\1.so/')"; \
		[ "$$new_so" = "$$so" ] || mv "$$so" "$$new_so"; \
	done
else
	$(call Build/PyMod3/PKG, PYTHON3_PYYAML, , \
		PYYAML_FORCE_LIBYAML=0 \
	)
endif

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYYAML_DIR)/.configured
	$(RM) -r $(PYTHON3_PYYAML_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYYAML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/yaml \
		$(PYTHON3_PYYAML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/_yaml \
		$(PYTHON3_PYYAML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/PyYAML-*.dist-info

$(PKG_FINISH)
