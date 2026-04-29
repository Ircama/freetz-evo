$(call PKG_INIT_BIN, 2.0.1)
$(PKG)_SOURCE:=pymicro-vad-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pymicro_vad-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pymicro-vad
$(PKG)_HASH:=51d188b3d02e5612a72f1c2a190d0c183daaeaf4bb012b83e1e458b9d104db8c
### WEBSITE:=https://github.com/rhasspy/pymicro-vad
### CVSREPO:=https://github.com/rhasspy/pymicro-vad
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pymicro_vad/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYMICRO_VAD, , \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYMICRO_VAD_DIR)/.configured
	$(RM) -r $(PYTHON3_PYMICRO_VAD_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYMICRO_VAD_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pymicro_vad \
		$(PYTHON3_PYMICRO_VAD_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pymicro_vad-*.dist-info

$(PKG_FINISH)
