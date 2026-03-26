$(call PKG_INIT_BIN, 4.0.0)
$(PKG)_SOURCE:=dbus-fast-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=dbus_fast-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/d/dbus-fast
$(PKG)_HASH:=e1d3ee49a4a81524d7caaa2d5a31fc71075a1c977b661df958cee24bef86b8fe
### WEBSITE:=https://github.com/Bluetooth-Devices/dbus-fast
### CHANGES:=https://github.com/Bluetooth-Devices/dbus-fast/releases
### CVSREPO:=https://github.com/Bluetooth-Devices/dbus-fast

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/dbus_fast/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) "Cython>=3,<3.3.0"
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) "poetry-core>=1.0.0"
	$(call Build/PyMod3/Pip, PYTHON3_DBUS_FAST, , REQUIRE_CYTHON=1)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_DBUS_FAST_DIR)/.configured
	$(RM) -r $(PYTHON3_DBUS_FAST_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_DBUS_FAST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/dbus_fast \
		$(PYTHON3_DBUS_FAST_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/dbus_fast-*.dist-info

$(PKG_FINISH)
