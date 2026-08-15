$(call PKG_INIT_LIB, 2.3.5)
# Project version 2.3.5, library SO version 3.2.3
$(PKG)_LIB_VERSION:=3.2.3
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f89e8e983ecfb4a5b4f5d8c2b9157ed18d15ed2e36246fa782f18abaea550e0d
$(PKG)_SITE:=https://github.com/FluidSynth/fluidsynth/archive/refs/tags
### WEBSITE:=https://www.fluidsynth.org/

$(PKG)_CATEGORY_LIBS:=Multimedia##Audio codecs
$(PKG)_BINARY:=$($(PKG)_DIR)/src/libfluidsynth.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libfluidsynth.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libfluidsynth.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += glib2 libsndfile

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -Denable-alsa=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-dbus=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-dsound=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-ladspa=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-midishare=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-oboe=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-opensles=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-pipewire=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-portaudio=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-sdl2=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-waveout=OFF
$(PKG)_CONFIGURE_OPTIONS += -Denable-oss=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(FLUIDSYNTH_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(FLUIDSYNTH_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(FLUIDSYNTH_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libfluidsynth.so*

$(PKG_FINISH)
