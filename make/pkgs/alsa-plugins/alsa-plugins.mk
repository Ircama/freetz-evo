$(call PKG_INIT_BIN, 1.2.12)
### WEBSITE:=https://www.alsa-project.org/wiki/Main_Page
### CHANGES:=https://www.alsa-project.org/wiki/Detailed_changes_v1.2.12_v1.2.13

$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=7bd8a83d304e8e2d86a25895d8dcb0ef0245a8df32e271959cdbdc6af39b66f2
$(PKG)_SITE:=https://www.alsa-project.org/files/pub/plugins

$(PKG)_PLUGIN_INSTALL_DIR:=$($(PKG)_DEST_DIR)/usr/lib/alsa-lib

# --- samplerate plugin ---
$(PKG)_SAMPLERATE_BINARY:=$($(PKG)_DIR)/rate/.libs/libasound_module_rate_samplerate.so
$(PKG)_SAMPLERATE_TARGET:=$($(PKG)_PLUGIN_INSTALL_DIR)/libasound_module_rate_samplerate.so

# --- speexrate plugin (built-in speex resampler, no external dep) ---
$(PKG)_SPEEXRATE_BINARY:=$($(PKG)_DIR)/pph/.libs/libasound_module_rate_speexrate.so
$(PKG)_SPEEXRATE_TARGET:=$($(PKG)_PLUGIN_INSTALL_DIR)/libasound_module_rate_speexrate.so

# --- lavrate plugin (ffmpeg/libswresample) ---
$(PKG)_LAVRATE_BINARY:=$($(PKG)_DIR)/rate-lav/.libs/libasound_module_rate_lavrate.so
$(PKG)_LAVRATE_TARGET:=$($(PKG)_PLUGIN_INSTALL_DIR)/libasound_module_rate_lavrate.so

# Conditional dependencies
$(PKG)_DEPENDS_ON += $(if $(FREETZ_LIB_libasound_WITH_SAMPLERATE),libsamplerate)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_LIB_libasound_WITH_LAVRATE),ffmpeg)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --disable-static

# Configure plugin subdirs based on user selection
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_LIB_libasound_WITH_SAMPLERATE),--enable-samplerate,--disable-samplerate)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_LIB_libasound_WITH_SPEEXRATE),--with-speex=builtin,--with-speex=no)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_LIB_libasound_WITH_LAVRATE),--enable-lavrate,--disable-lavrate)

# Force fixed-point arithmetic for the built-in speex resampler (pph/).
# Without -DFIXED_POINT, arch.h defaults to float for spx_word16_t, causing
# heavy soft-float emulation on MIPS and audio stuttering.
ifneq ($(strip $(FREETZ_LIB_libasound_WITH_SPEEXRATE)),)
$(PKG)_CONFIGURE_ENV += CFLAGS="$(TARGET_CFLAGS) -DFIXED_POINT"
endif

# Disable plugins we don't use
$(PKG)_CONFIGURE_OPTIONS += --disable-a52 --disable-oss --disable-jack --disable-pulseaudio
$(PKG)_CONFIGURE_OPTIONS += --disable-maemo-plugin --disable-maemo-resource-manager
$(PKG)_CONFIGURE_OPTIONS += --disable-mix --disable-usbstream --disable-arcamav --disable-aaf

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

# Build all enabled plugin subdirectories
$($(PKG)_DIR)/.build: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(ALSA_PLUGINS_DIR)
	@touch $@

# Collect only enabled plugin targets for the main dependency
$(PKG)_TARGETS :=

ifneq ($(strip $(FREETZ_LIB_libasound_WITH_SAMPLERATE)),)
$(PKG)_TARGETS += $($(PKG)_SAMPLERATE_TARGET)
$($(PKG)_SAMPLERATE_TARGET): $($(PKG)_DIR)/.build
	mkdir -p $(dir $(ALSA_PLUGINS_SAMPLERATE_TARGET))
	cp -a $(ALSA_PLUGINS_DIR)/rate/.libs/libasound_module_rate_samplerate.so $(dir $(ALSA_PLUGINS_SAMPLERATE_TARGET))
	$(TARGET_STRIP) $(ALSA_PLUGINS_SAMPLERATE_TARGET)
endif

ifneq ($(strip $(FREETZ_LIB_libasound_WITH_SPEEXRATE)),)
$(PKG)_TARGETS += $($(PKG)_SPEEXRATE_TARGET)
$($(PKG)_SPEEXRATE_TARGET): $($(PKG)_DIR)/.build
	mkdir -p $(dir $(ALSA_PLUGINS_SPEEXRATE_TARGET))
	cp -a $(ALSA_PLUGINS_DIR)/pph/.libs/libasound_module_rate_speexrate.so $(dir $(ALSA_PLUGINS_SPEEXRATE_TARGET))
	$(TARGET_STRIP) $(ALSA_PLUGINS_SPEEXRATE_TARGET)
endif

ifneq ($(strip $(FREETZ_LIB_libasound_WITH_LAVRATE)),)
$(PKG)_TARGETS += $($(PKG)_LAVRATE_TARGET)
$($(PKG)_LAVRATE_TARGET): $($(PKG)_DIR)/.build
	mkdir -p $(dir $(ALSA_PLUGINS_LAVRATE_TARGET))
	cp -a $(ALSA_PLUGINS_DIR)/rate-lav/.libs/libasound_module_rate_lavrate.so $(dir $(ALSA_PLUGINS_LAVRATE_TARGET))
	$(TARGET_STRIP) $(ALSA_PLUGINS_LAVRATE_TARGET)
endif

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGETS)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ALSA_PLUGINS_DIR) clean
	$(RM) -r \
		$(ALSA_PLUGINS_DIR)/rate/.libs \
		$(ALSA_PLUGINS_DIR)/pph/.libs \
		$(ALSA_PLUGINS_DIR)/rate-lav/.libs \
		$(ALSA_PLUGINS_DIR)/.build 2>/dev/null || true

$(pkg)-uninstall:
	$(RM) -r $($(PKG)_PLUGIN_INSTALL_DIR)

$(PKG_FINISH)
