$(call PKG_INIT_BIN, 14.4.2)
### WEBSITE:=https://sourceforge.net/projects/sox/
### CHANGES:=https://sourceforge.net/p/sox/code/

$(PKG)_CATEGORY_PKGS:=Audio

$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=81a6956d4330e75b5827316e44ae381e6f1e8928003c6aa45896da9041ea149c
$(PKG)_SITE:=https://downloads.sourceforge.net/project/sox/sox/$($(PKG)_VERSION)

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/sox
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/sox

$(PKG)_LIBRARY:=$($(PKG)_DIR)/src/.libs/libsox.so.3.0.0
$(PKG)_TARGET_LIBRARY:=$($(PKG)_DEST_LIBDIR)/libsox.so.3.0.0

$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_ID3TAG),iconv)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_LIBSNDFILE),libsndfile)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_MP3),libmad)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_MP3),mpg123)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_VORBIS),libvorbis)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_VORBIS),libogg)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_FLAC),flac)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_WAVPACK),libwavpack)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_OPUS),opus)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_GSM),libgsm)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_PNG),libpng)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_SOX_WITH_ID3TAG),libid3tag)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_ID3TAG
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_LIBSNDFILE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_MP3
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_VORBIS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_FLAC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_WAVPACK
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_OPUS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_GSM
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_PNG
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_SOX_WITH_ID3TAG

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --without-libltdl
$(PKG)_CONFIGURE_OPTIONS += --without-libao
$(PKG)_CONFIGURE_OPTIONS += --without-lame
$(PKG)_CONFIGURE_OPTIONS += --without-twolame
$(PKG)_CONFIGURE_OPTIONS += --without-ffmpeg
$(PKG)_CONFIGURE_OPTIONS += --without-amrnb
$(PKG)_CONFIGURE_OPTIONS += --without-amrwb
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_LIBSNDFILE),--with-libsndfile,--without-libsndfile)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_MP3),--with-mad,--without-mad)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_MP3),--with-mpg123,--without-mpg123)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_VORBIS),--with-oggvorbis,--without-oggvorbis)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_FLAC),--with-flac,--without-flac)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_WAVPACK),--with-wavpack,--without-wavpack)
$(PKG)_CONFIGURE_OPTIONS += --without-opus
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_GSM),--with-gsm,--without-gsm)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_PNG),--with-png,--without-png)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_ID3TAG),--with-iconv,--without-iconv)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_SOX_WITH_ID3TAG),--with-id3tag,--without-id3tag)

# -Ofast implies -ffast-math which optimizes infinity comparisons (HUGE_VAL)
# to always be true, breaking sox's compression-factor validation (sox.c:2912).
$(PKG)_CONFIGURE_ENV += CFLAGS="$(TARGET_CFLAGS) -fno-fast-math"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

# Create missing .deps files to prevent parallel make failures
$(PKG)_CONFIGURE_POST_CMDS += \
	cd src && \
	for f in $$(grep "^include " Makefile | sed 's/include \.\/\$$(DEPDIR)\///'); do \
		[ -f ".deps/$$f" ] || touch ".deps/$$f"; \
	done

$($(PKG)_BINARY) $($(PKG)_LIBRARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(SOX_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)
	ln -sf sox $(dir $(SOX_TARGET_BINARY))play
	ln -sf sox $(dir $(SOX_TARGET_BINARY))rec

$($(PKG)_TARGET_LIBRARY): $($(PKG)_LIBRARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_TARGET_LIBRARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(SOX_DIR) clean
	$(RM) -r $(SOX_DIR)/src/.libs 2>/dev/null || true

$(pkg)-uninstall:
	$(RM) $(SOX_TARGET_BINARY)
	$(RM) $(dir $(SOX_TARGET_BINARY))play
	$(RM) $(dir $(SOX_TARGET_BINARY))rec
	$(RM) $(SOX_TARGET_DIR)/libsox*.so*

$(PKG_FINISH)
