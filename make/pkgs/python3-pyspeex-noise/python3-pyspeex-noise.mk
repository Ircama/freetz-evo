$(call PKG_INIT_BIN, 2.0.0)
$(PKG)_SOURCE:=pyspeex-noise-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pyspeex_noise-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pyspeex-noise
$(PKG)_HASH:=6fdb16e59d7a353690661c71e35e2c91972419bfd79dfe37db66ead0e95e7827
### WEBSITE:=https://github.com/rhasspy/pyspeex-noise
### CVSREPO:=https://github.com/rhasspy/pyspeex-noise

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyspeex_noise/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	@mkdir -p $(PYTHON3_PYSPEEX_NOISE_DIR)/src
	@if [ ! -f $(PYTHON3_PYSPEEX_NOISE_DIR)/src/speex_noise.cpp ]; then \
		cp ./make/pkgs/python3-pyspeex-noise/files/speex_noise.cpp \
			$(PYTHON3_PYSPEEX_NOISE_DIR)/src/speex_noise.cpp; \
	fi
	$(call Build/PyMod3/Pip, PYTHON3_PYSPEEX_NOISE, , \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYSPEEX_NOISE_DIR)/.configured
	$(RM) -r $(PYTHON3_PYSPEEX_NOISE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYSPEEX_NOISE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyspeex_noise \
		$(PYTHON3_PYSPEEX_NOISE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyspeex_noise-*.dist-info

$(PKG_FINISH)
