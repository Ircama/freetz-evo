$(call PKG_INIT_BIN, 3.2.2)
$(PKG)_SOURCE:=ha-ffmpeg-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=ha_ffmpeg-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/h/ha-ffmpeg
$(PKG)_HASH:=80e4a77b3eda73df456ec9cc3295a898ed7cbb8cd2d59798f10e8c10a8e6c401
### WEBSITE:=https://github.com/home-assistant-libs/ha-ffmpeg
### CVSREPO:=https://github.com/home-assistant-libs/ha-ffmpeg

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-async-timeout

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/haffmpeg/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_HA_FFMPEG, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_HA_FFMPEG_DIR)/.configured
	$(RM) -r $(PYTHON3_HA_FFMPEG_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_HA_FFMPEG_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/haffmpeg \
		$(PYTHON3_HA_FFMPEG_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ha_ffmpeg-*.dist-info

$(PKG_FINISH)
