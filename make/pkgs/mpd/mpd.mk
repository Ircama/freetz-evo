$(call PKG_INIT_BIN, 0.24.7)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=d497c07df2a78600cf60e4a47c677df9cf9ac1daecb3c163147b643a6e2e0882
$(PKG)_SITE:=https://github.com/MusicPlayerDaemon/MPD/archive/refs/tags
### WEBSITE:=https://www.musicpd.org/
### MANPAGE:=https://mpd.readthedocs.io/en/stable/user.html
### CHANGES:=https://github.com/MusicPlayerDaemon/MPD/releases
### CVSREPO:=https://github.com/MusicPlayerDaemon/MPD
### STEWARD:=Ircama
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/mpd/

$(PKG)_CATEGORY:=Audio

$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/mpd
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/mpd

$(PKG)_DEPENDS_ON += meson-host
$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)
$(PKG)_DEPENDS_ON += jemalloc
$(PKG)_DEPENDS_ON += alsa-lib flac libid3tag libmad libogg libvorbis zlib
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_MPD_WITH_URI_INPUTS),curl)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_MPD_WITH_SQLITE),sqlite)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_MPD_WITH_BZIP2),bzip2)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_MPD_WITH_FFMPEG),ffmpeg)

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libjemalloc
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MPD_WITH_URI_INPUTS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MPD_WITH_SQLITE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MPD_WITH_BZIP2
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MPD_WITH_FFMPEG
$(PKG)_REBUILD_SUBOPTS += $(if $(FREETZ_PACKAGE_MPD_WITH_FFMPEG),FREETZ_PACKAGE_FFMPEG_VERSION_ABANDON)
$(PKG)_REBUILD_SUBOPTS += $(if $(FREETZ_PACKAGE_MPD_WITH_URI_INPUTS),$(filter FREETZ_LIB_libcurl_%,$(CURL_REBUILD_SUBOPTS)))

MPD_MESON_ENV := PATH="$(abspath $(TOOLS_DIR)/path):$(subst ",,$(TARGET_PATH))" $(FREETZ_LD_RUN_PATH) FREETZ_LIBRARY_DIR="$(FREETZ_LIBRARY_DIR)"

$(PKG)_CONFIGURE_ENV += PATH="$(abspath $(TOOLS_DIR)/path):$(subst ",,$(TARGET_PATH))"
$(PKG)_CONFIGURE_ENV += FREETZ_LIBRARY_DIR="$(FREETZ_LIBRARY_DIR)"

$(PKG)_CONFIGURE_OPTIONS += -D documentation=disabled
$(PKG)_CONFIGURE_OPTIONS += -D html_manual=false
$(PKG)_CONFIGURE_OPTIONS += -D manpages=false
$(PKG)_CONFIGURE_OPTIONS += -D syslog=disabled
$(PKG)_CONFIGURE_OPTIONS += -D systemd=disabled
$(PKG)_CONFIGURE_OPTIONS += -D dbus=disabled
$(PKG)_CONFIGURE_OPTIONS += -D zeroconf=disabled
$(PKG)_CONFIGURE_OPTIONS += -D sqlite=$(if $(FREETZ_PACKAGE_MPD_WITH_SQLITE),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D pcre=disabled
$(PKG)_CONFIGURE_OPTIONS += -D icu=disabled
$(PKG)_CONFIGURE_OPTIONS += -D iconv=disabled
$(PKG)_CONFIGURE_OPTIONS += -D expat=disabled
$(PKG)_CONFIGURE_OPTIONS += -D curl=$(if $(FREETZ_PACKAGE_MPD_WITH_URI_INPUTS),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D webdav=disabled
$(PKG)_CONFIGURE_OPTIONS += -D nfs=disabled
$(PKG)_CONFIGURE_OPTIONS += -D qobuz=disabled
$(PKG)_CONFIGURE_OPTIONS += -D upnp=disabled
$(PKG)_CONFIGURE_OPTIONS += -D libmpdclient=disabled
$(PKG)_CONFIGURE_OPTIONS += -D io_uring=disabled
$(PKG)_CONFIGURE_OPTIONS += -D ipv6=disabled
$(PKG)_CONFIGURE_OPTIONS += -D neighbor=false
$(PKG)_CONFIGURE_OPTIONS += -D database=true
$(PKG)_CONFIGURE_OPTIONS += -D inotify=true
$(PKG)_CONFIGURE_OPTIONS += -D tcp=true
$(PKG)_CONFIGURE_OPTIONS += -D local_socket=true
$(PKG)_CONFIGURE_OPTIONS += -D daemon=true
$(PKG)_CONFIGURE_OPTIONS += -D dsd=false
$(PKG)_CONFIGURE_OPTIONS += -D cue=false
$(PKG)_CONFIGURE_OPTIONS += -D bzip2=$(if $(FREETZ_PACKAGE_MPD_WITH_BZIP2),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D iso9660=disabled
$(PKG)_CONFIGURE_OPTIONS += -D zzip=disabled
$(PKG)_CONFIGURE_OPTIONS += -D cdio_paranoia=disabled
$(PKG)_CONFIGURE_OPTIONS += -D mms=disabled
$(PKG)_CONFIGURE_OPTIONS += -D smbclient=disabled
$(PKG)_CONFIGURE_OPTIONS += -D id3tag=enabled
$(PKG)_CONFIGURE_OPTIONS += -D flac=enabled
$(PKG)_CONFIGURE_OPTIONS += -D mad=enabled
$(PKG)_CONFIGURE_OPTIONS += -D vorbis=enabled
$(PKG)_CONFIGURE_OPTIONS += -D adplug=disabled
$(PKG)_CONFIGURE_OPTIONS += -D audiofile=disabled
$(PKG)_CONFIGURE_OPTIONS += -D faad=disabled
$(PKG)_CONFIGURE_OPTIONS += -D ffmpeg=$(if $(FREETZ_PACKAGE_MPD_WITH_FFMPEG),enabled,disabled)
$(PKG)_CONFIGURE_OPTIONS += -D fluidsynth=disabled
$(PKG)_CONFIGURE_OPTIONS += -D gme=disabled
$(PKG)_CONFIGURE_OPTIONS += -D mikmod=disabled
$(PKG)_CONFIGURE_OPTIONS += -D modplug=disabled
$(PKG)_CONFIGURE_OPTIONS += -D openmpt=disabled
$(PKG)_CONFIGURE_OPTIONS += -D mpcdec=disabled
$(PKG)_CONFIGURE_OPTIONS += -D mpg123=disabled
$(PKG)_CONFIGURE_OPTIONS += -D opus=disabled
$(PKG)_CONFIGURE_OPTIONS += -D sidplay=disabled
$(PKG)_CONFIGURE_OPTIONS += -D sndfile=disabled
$(PKG)_CONFIGURE_OPTIONS += -D tremor=disabled
$(PKG)_CONFIGURE_OPTIONS += -D wavpack=disabled
$(PKG)_CONFIGURE_OPTIONS += -D wildmidi=disabled
$(PKG)_CONFIGURE_OPTIONS += -D vorbisenc=disabled
$(PKG)_CONFIGURE_OPTIONS += -D lame=disabled
$(PKG)_CONFIGURE_OPTIONS += -D twolame=disabled
$(PKG)_CONFIGURE_OPTIONS += -D shine=disabled
$(PKG)_CONFIGURE_OPTIONS += -D wave_encoder=false
$(PKG)_CONFIGURE_OPTIONS += -D libsamplerate=disabled
$(PKG)_CONFIGURE_OPTIONS += -D soxr=disabled
$(PKG)_CONFIGURE_OPTIONS += -D alsa=enabled
$(PKG)_CONFIGURE_OPTIONS += -D ao=disabled
$(PKG)_CONFIGURE_OPTIONS += -D fifo=false
$(PKG)_CONFIGURE_OPTIONS += -D httpd=false
$(PKG)_CONFIGURE_OPTIONS += -D jack=disabled
$(PKG)_CONFIGURE_OPTIONS += -D openal=disabled
$(PKG)_CONFIGURE_OPTIONS += -D oss=disabled
$(PKG)_CONFIGURE_OPTIONS += -D pipe=false
$(PKG)_CONFIGURE_OPTIONS += -D pipewire=disabled
$(PKG)_CONFIGURE_OPTIONS += -D pulse=disabled
$(PKG)_CONFIGURE_OPTIONS += -D recorder=false
$(PKG)_CONFIGURE_OPTIONS += -D shout=disabled
$(PKG)_CONFIGURE_OPTIONS += -D snapcast=false
$(PKG)_CONFIGURE_OPTIONS += -D sndio=disabled
$(PKG)_CONFIGURE_OPTIONS += -D solaris_output=disabled

$(PKG)_CONFIGURE_PRE_CMDS += $(SED) -r -i \
	-e "s|^pkg-?config[[:space:]]*=.*|pkg-config        = 'pkg-config'|" \
	-e "s|^python[[:space:]]*=.*|python            = '$(abspath $(TOOLS_DIR)/path/python3)'|" \
	-e "s|^cmake[[:space:]]*=.*|cmake             = '$(abspath $(TOOLS_DIR)/path/cmake)'|" \
	meson.freetz;

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_MESON)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	cmd() { $(MPD_MESON_ENV) $(MESON) "$$@" $(SILENT) || { $(call ERROR,1,$(BUILD_FAIL_MSG)) } ; }; $(call _ECHO,building) cmd compile \
		-C $(MPD_DIR)/builddir/

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	cmd() { $(MPD_MESON_ENV) $(MESON) "$$@" $(SILENT) || { $(call ERROR,1,$(BUILD_FAIL_MSG)) } ; }; $(call _ECHO,building) cmd install \
		--no-rebuild \
		--destdir "$(abspath $(MPD_DEST_DIR))" \
		-C $(MPD_DIR)/builddir/
	$(RM) -r \
		$(MPD_DEST_DIR)/usr/include \
		$(MPD_DEST_DIR)/usr/lib/pkgconfig \
		$(MPD_DEST_DIR)/usr/share
	$(RM) $(MPD_DEST_DIR)/usr/lib/libfmt.a
	@if [ "$(FREETZ_SEPARATE_AVM_UCLIBC)" = "y" ]; then \
		$(PATCHELF_TARGET) --set-interpreter $(FREETZ_LIBRARY_DIR)/ld-uClibc.so.1 $(MPD_DEST_DIR)/usr/bin/mpd; \
	fi
	$(TARGET_STRIP) $(MPD_TARGET_BINARY) 2>/dev/null || true

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBNINJA) -C $(MPD_DIR)/builddir/ clean
	$(RM) $(MPD_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(MPD_TARGET_BINARY)

$(PKG_FINISH)