$(call PKG_INIT_BIN, 2.0.3)
$(PKG)_SOURCE:=fnv-hash-fast-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=fnv_hash_fast-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/f/fnv-hash-fast
$(PKG)_HASH:=57b499a80ea8f7daf901aff047377264ef21577b40575183807dba37bcc00d6f
### WEBSITE:=https://github.com/bluetooth-devices/fnv-hash-fast
### CHANGES:=https://github.com/bluetooth-devices/fnv-hash-fast/releases
### CVSREPO:=https://github.com/bluetooth-devices/fnv-hash-fast
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += python3-fnvhash

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fnv_hash_fast/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Build with Cython C extension for performance.
# The build_ext.py gracefully falls back to pure Python if Cython is unavailable.
$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) Cython==3.2.0 $(SILENT)
	$(call Build/PyMod3/PKG, PYTHON3_FNV_HASH_FAST, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_FNV_HASH_FAST_DIR)/.configured
	$(RM) -r $(PYTHON3_FNV_HASH_FAST_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_FNV_HASH_FAST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fnv_hash_fast \
		$(PYTHON3_FNV_HASH_FAST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fnv_hash_fast-*.dist-info

$(PKG_FINISH)
