$(call PKG_INIT_LIB, 8.6.16)
$(PKG)_LIB_VERSION:=8.6
$(PKG)_SOURCE:=$(pkg)$($(PKG)_VERSION)-src.tar.gz
$(PKG)_HASH:=be9f94d3575d4b3099d84bc3c10de8994df2d7aa405208173c709cc404a7e5fe
$(PKG)_SITE:=https://prdownloads.sourceforge.net/tcl
### WEBSITE:=https://www.tcl.tk/
### CHANGES:=https://core.tcl-lang.org/tk/timeline
### CVSREPO:=https://core.tcl-lang.org/tk

$(PKG)_BINARY:=$($(PKG)_DIR)/unix/libtk$(TK_LIB_VERSION).so
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtk$(TK_LIB_VERSION).so
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libtk$(TK_LIB_VERSION).so

$(PKG)_BUILD_SUBDIR:=unix

$(PKG)_DEPENDS_ON += tcl
$(PKG)_DEPENDS_ON += $(if $(FREETZ_LIB_libX11),libX11)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_LIB_libXt),libXt)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-threads
$(PKG)_CONFIGURE_OPTIONS += --disable-man-symlinks
$(PKG)_CONFIGURE_OPTIONS += --disable-man-compression
$(PKG)_CONFIGURE_OPTIONS += --with-tcl=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib

# X11 client libraries for remote display connectivity.
# Tk uses X11 to connect to a remote X server via DISPLAY=host:screen.
$(PKG)_CONFIGURE_ENV += CPPFLAGS="-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_ENV += LDFLAGS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib"

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libtk
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libX11
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libXt


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TK_DIR)/unix
	touch $@

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.compiled
	$(SUBMAKE) -C $(TK_DIR)/unix \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtk$(TK_LIB_VERSION).a
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtkstub$(TK_LIB_VERSION).a
	# Tk does not use libtool, no .la file

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	mkdir -p $(dir $@)
	cp -a $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtk$(TK_LIB_VERSION).so* $(dir $@)
	chmod +w $(dir $@)libtk$(TK_LIB_VERSION).so* 2>/dev/null || true
	# Strip the real file (skip symlinks)
	for f in $(dir $@)libtk$(TK_LIB_VERSION).so*; do \
		if [ ! -L "$$f" ]; then $(TARGET_STRIP) "$$f"; fi; \
	done

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(TK_DIR)/unix clean
	$(RM) $(TK_DIR)/.configured
	$(RM) $(TK_DIR)/.compiled
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtk* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/tk*.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/tk*.pc

$(pkg)-uninstall:
	$(RM) $(TK_TARGET_DIR)/libtk*.so*

$(PKG_FINISH)
