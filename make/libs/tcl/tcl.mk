$(call PKG_INIT_LIB, 8.6.16)
$(PKG)_LIB_VERSION:=8.6
$(PKG)_SOURCE:=$(pkg)$($(PKG)_VERSION)-src.tar.gz
$(PKG)_HASH:=91cb8fa61771c63c262efb553059b7c7ad6757afa5857af6265e4b0bdc2a14a5
$(PKG)_SITE:=https://prdownloads.sourceforge.net/tcl
### WEBSITE:=https://www.tcl.tk/
### CHANGES:=https://core.tcl-lang.org/tcl/timeline
### CVSREPO:=https://core.tcl-lang.org/tcl

$(PKG)_BINARY:=$($(PKG)_DIR)/unix/libtcl$(TCL_LIB_VERSION).so
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtcl$(TCL_LIB_VERSION).so
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libtcl$(TCL_LIB_VERSION).so

$(PKG)_BUILD_SUBDIR:=unix

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-threads
$(PKG)_CONFIGURE_OPTIONS += --disable-man-symlinks
$(PKG)_CONFIGURE_OPTIONS += --disable-man-compression
$(PKG)_CONFIGURE_OPTIONS += tcl_cv_strtod_buggy=1

$(PKG)_CONFIGURE_ENV += ac_cv_func_strtod=yes
$(PKG)_CONFIGURE_ENV += tcl_cv_strtod_buggy=1

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libtcl

$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TCL_DIR)/unix
	touch $@

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.compiled
	$(SUBMAKE) -C $(TCL_DIR)/unix \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtcl$(TCL_LIB_VERSION).a
	# Keep libtclstub*.a in staging - needed by Tk and other stub-using packages
	# Tcl does not use libtool, no .la file

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	mkdir -p $(dir $@)
	cp -a $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtcl$(TCL_LIB_VERSION).so* $(dir $@)
	chmod +w $(dir $@)libtcl$(TCL_LIB_VERSION).so* 2>/dev/null || true
	# Strip the real file (skip symlinks)
	for f in $(dir $@)libtcl$(TCL_LIB_VERSION).so*; do \
		if [ ! -L "$$f" ]; then $(TARGET_STRIP) "$$f"; fi; \
	done
	@if [ "$(FREETZ_SEPARATE_AVM_UCLIBC)" = "y" ]; then \
		for f in $(dir $@)libtcl$(TCL_LIB_VERSION).so*; do \
			[ -L "$$f" ] && continue; \
			$(PATCHELF_TARGET) --set-rpath $(FREETZ_LIBRARY_DIR) "$$f" 2>/dev/null || true; \
		done; \
	fi
	# Install Tcl library scripts (init.tcl etc.) needed by wish/Tcl applications
	mkdir -p $(TCL_DEST_DIR)/usr/lib
	cp -a $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/tcl$(TCL_LIB_VERSION) $(TCL_DEST_DIR)/usr/lib/
	cp -a $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/tcl8 $(TCL_DEST_DIR)/usr/lib/

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(TCL_DIR)/unix clean
	$(RM) $(TCL_DIR)/.configured
	$(RM) $(TCL_DIR)/.compiled
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtcl* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/tcl*.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/tcl*.pc

$(pkg)-uninstall:
	$(RM) $(TCL_TARGET_DIR)/libtcl*.so*
	$(RM) -r $(TCL_DEST_DIR)/usr/lib/tcl$(TCL_LIB_VERSION) $(TCL_DEST_DIR)/usr/lib/tcl8

$(PKG_FINISH)
