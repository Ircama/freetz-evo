$(call PKG_INIT_BIN, 2.11.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=2bbdcd6bbbae301d734214eab791e3755baf4d16db24a44626961a489aa5e0f7
$(PKG)_SITE:=https://github.com/cmus/cmus/archive
### WEBSITE:=https://cmus.github.io/
### CHANGES:=https://github.com/cmus/cmus/releases
### CVSREPO:=https://github.com/cmus/cmus

$(PKG)_CATEGORY:=Audio

$(PKG)_BINARY:=$($(PKG)_DIR)/cmus
$(PKG)_TARGET_INSTALL_MARKER:=$($(PKG)_DEST_DIR)/.installed

$(PKG)_DEPENDS_ON += alsa-lib libatomic ncursesw libmad flac libvorbis
$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)

$(PKG)_CONFIGURE_ENV += PKG_CONFIG=/usr/bin/pkg-config
$(PKG)_CONFIGURE_ENV += PKG_CONFIG_LIBDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig"
$(PKG)_CONFIGURE_ENV += PKG_CONFIG_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	(cd $(CMUS_DIR) && \
		$(TARGET_CONFIGURE_PRE_CMDS) \
		$(TARGET_CONFIGURE_ENV) \
		$(CMUS_CONFIGURE_ENV) \
		./configure \
			prefix=/usr \
			CONFIG_ALSA=y \
			CONFIG_MAD=y \
			CONFIG_FLAC=y \
			CONFIG_VORBIS=y \
			CONFIG_TREMOR=n \
			CONFIG_OSS=n \
			CONFIG_PULSE=n \
			CONFIG_JACK=n \
			CONFIG_SAMPLERATE=n \
			CONFIG_AO=n \
			CONFIG_ARTS=n \
			CONFIG_SNDIO=n \
			CONFIG_SUN=n \
			CONFIG_WAVEOUT=n \
			CONFIG_ROAR=n \
			CONFIG_COREAUDIO=n \
			CONFIG_DISCID=n \
			CONFIG_CDDB=n \
			CONFIG_CDIO=n \
			CONFIG_FFMPEG=n \
			CONFIG_MPC=n \
			CONFIG_MP4=n \
			CONFIG_AAC=n \
			CONFIG_OPUS=n \
			CONFIG_WAVPACK=n \
			CONFIG_VTX=n \
			CONFIG_MIKMOD=n \
			CONFIG_BASS=n \
			CONFIG_MODPLUG=n \
			CONFIG_MPRIS=n \
	) $(SILENT)
	sed -i -e '/^COMPAT_LIBS =/ s,$$, -latomic,' $(CMUS_DIR)/config.mk
	touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(CMUS_DIR)

$($(PKG)_TARGET_INSTALL_MARKER): $($(PKG)_BINARY)
	(cd $(CMUS_DIR) && DESTDIR="$(abspath $(CMUS_DEST_DIR))" $(MAKE) install) $(SILENT)
	$(RM) -r \
		$(CMUS_DEST_DIR)/usr/share/doc \
		$(CMUS_DEST_DIR)/usr/share/man
	@if [ "$(FREETZ_SEPARATE_AVM_UCLIBC)" = "y" ]; then \
		$(FREETZ_BASE_DIR)/$(TOOLS_DIR)/patchelf-target --set-interpreter $(FREETZ_LIBRARY_DIR)/ld-uClibc.so.1 $(CMUS_DEST_DIR)/usr/bin/cmus; \
		$(FREETZ_BASE_DIR)/$(TOOLS_DIR)/patchelf-target --set-interpreter $(FREETZ_LIBRARY_DIR)/ld-uClibc.so.1 $(CMUS_DEST_DIR)/usr/bin/cmus-remote; \
	fi
	$(TARGET_STRIP) \
		$(CMUS_DEST_DIR)/usr/bin/cmus \
		$(CMUS_DEST_DIR)/usr/bin/cmus-remote 2>/dev/null || true
	@if [ -d "$(CMUS_DEST_DIR)/usr/lib/cmus" ]; then \
		find "$(CMUS_DEST_DIR)/usr/lib/cmus" -type f -name '*.so' -exec $(TARGET_STRIP) {} + 2>/dev/null || true; \
	fi
	touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_INSTALL_MARKER)


$(pkg)-clean:
	-$(SUBMAKE) -C $(CMUS_DIR) clean
	$(RM) $(CMUS_DIR)/.configured $(CMUS_DIR)/.installed

$(pkg)-uninstall:
	$(RM) -r \
		$(CMUS_DEST_DIR)/usr/bin/cmus \
		$(CMUS_DEST_DIR)/usr/bin/cmus-remote \
		$(CMUS_DEST_DIR)/usr/lib/cmus \
		$(CMUS_DEST_DIR)/usr/share/cmus \
		$(CMUS_TARGET_INSTALL_MARKER)

$(PKG_FINISH)