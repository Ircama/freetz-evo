$(call PKG_INIT_BIN, 0.15.0)
$(PKG)_SOURCE:=hidapi-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=hidapi-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/h/hidapi
$(PKG)_HASH:=ecbc265cbe8b7b88755f421e0ba25f084091ec550c2b90ff9e8ddd4fcd540311
### WEBSITE:=https://github.com/trezor/cython-hidapi
### CHANGES:=https://github.com/trezor/cython-hidapi/releases
### CVSREPO:=https://github.com/trezor/cython-hidapi

# Cython bindings to the embedded hidapi C source (libusb backend).
# The hidraw/udev extension is skipped via the freetz patch (see patches/) and
# the HIDAPI_WITHOUT_HIDRAW=1 env below: the FritzBox has no udev and no kernel
# HID stack, so -ludev would not link. Only the libusb backend is required.
#
# Built with Build/PyMod3/PKG (like ciso8601) instead of Build/PyMod3/Pip:
# the Pip variant passes the target python include via setuptools
# --config-settings, which is NOT honoured here, so the MIPS cross-compiler
# falls back to the HOST python headers (tools/build/usr/include/python3.14)
# and fails with "LONG_BIT definition appears wrong for platform". PKG passes
# --include-dirs=<PYTHON3_STAGING_INC_DIR> on the build_ext command line,
# which always shadows the host include.
$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += libusb1

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/hid.cpython-$(subst .,,$(PYTHON3_MAJOR_VERSION)).so

# Cross pkg-config: setup.py resolves libusb-1.0 at setup- AND build-time.
$(PKG)_PKG_CONFIG_DIR:=$(TARGET_TOOLCHAIN_STAGING_DIR)/lib/pkgconfig:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig:$(TARGET_MAKE_PATH)/../lib/pkgconfig

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) "Cython>=3,<4" $(SILENT)
	$(call Build/PyMod3/PKG, PYTHON3_HIDAPI, , \
		HIDAPI_WITHOUT_HIDRAW=1 \
		PKG_CONFIG=/usr/bin/pkg-config \
		PKG_CONFIG_ALLOW_CROSS=1 \
		PKG_CONFIG_PATH="$(PYTHON3_HIDAPI_PKG_CONFIG_DIR)" \
		PKG_CONFIG_LIBDIR="$(PYTHON3_HIDAPI_PKG_CONFIG_DIR)" \
	)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_HIDAPI_DIR)/.configured
	$(RM) -r $(PYTHON3_HIDAPI_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_HIDAPI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/hid.cpython-*.so \
		$(PYTHON3_HIDAPI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/hidapi-*.dist-info

$(PKG_FINISH)
