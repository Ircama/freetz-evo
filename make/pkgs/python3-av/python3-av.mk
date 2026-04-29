$(call PKG_INIT_BIN, 16.0.1)
$(PKG)_SOURCE:=av-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=av-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/a/av
$(PKG)_HASH:=dd2ce779fa0b5f5889a6d9e00fbbbc39f58e247e52d31044272648fe16ff1dbf
### WEBSITE:=https://pyav.basswood-io.com/
### MANPAGE:=https://pyav.basswood-io.com/docs/stable/
### CHANGES:=https://github.com/PyAV-Org/PyAV/releases
### CVSREPO:=https://github.com/PyAV-Org/PyAV
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += ffmpeg

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/av/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) "Cython>=3.1.0,<4" $(SILENT)
	$(call Build/PyMod3/PKG, PYTHON3_AV, , \
		PKG_CONFIG=pkg-config \
		PKG_CONFIG_PATH="$(TARGET_MAKE_PATH)/../lib/pkgconfig" \
		PKG_CONFIG_LIBDIR="$(TARGET_MAKE_PATH)/../lib/pkgconfig" \
	)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_AV_DIR)/.configured
	$(RM) -r $(PYTHON3_AV_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_AV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/av \
		$(PYTHON3_AV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/av-*.dist-info \
		$(PYTHON3_AV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/av-*.egg-info

$(PKG_FINISH)
