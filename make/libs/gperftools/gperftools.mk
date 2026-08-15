$(call PKG_INIT_LIB, 2.18.1)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=d18d919175f9e4d740ace6b52f0f4f91284160c454e91b36ffd6456282a02206
$(PKG)_SITE:=https://github.com/gperftools/gperftools/releases/download/$(pkg)-$($(PKG)_VERSION)
### WEBSITE:=https://gperftools.github.io/gperftools/
### MANPAGE:=https://gperftools.github.io/gperftools/tcmalloc.html
### CHANGES:=https://github.com/gperftools/gperftools/releases
### CVSREPO:=https://github.com/gperftools/gperftools

$(PKG)_CATEGORY_LIBS:=Memory allocators

# libtool version-info current:revision:age
# TCMALLOC_SO_VERSION=10:5:6  -> soname = current-age = 4
# PROFILER_SO_VERSION=5:19:5  -> soname = current-age = 0
$(PKG)_TCMALLOC_LIB_VERSION:=4.6.5
$(PKG)_PROFILER_LIB_VERSION:=0.5.19

$(PKG)_TCMALLOC_MINIMAL_BINARY:=$($(PKG)_DIR)/.libs/libtcmalloc_minimal.so.$($(PKG)_TCMALLOC_LIB_VERSION)
$(PKG)_TCMALLOC_MINIMAL_STAGING:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtcmalloc_minimal.so.$($(PKG)_TCMALLOC_LIB_VERSION)
$(PKG)_TCMALLOC_MINIMAL_TARGET:=$($(PKG)_TARGET_DIR)/libtcmalloc_minimal.so.$($(PKG)_TCMALLOC_LIB_VERSION)

$(PKG)_PROFILER_BINARY:=$($(PKG)_DIR)/.libs/libprofiler.so.$($(PKG)_PROFILER_LIB_VERSION)
$(PKG)_PROFILER_STAGING:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libprofiler.so.$($(PKG)_PROFILER_LIB_VERSION)
$(PKG)_PROFILER_TARGET:=$($(PKG)_TARGET_DIR)/libprofiler.so.$($(PKG)_PROFILER_LIB_VERSION)

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_ENV += ac_cv_have_pthread_setspecific_with___thread=no

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --disable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-debugalloc
$(PKG)_CONFIGURE_OPTIONS += --disable-heap-checker
$(PKG)_CONFIGURE_OPTIONS += --disable-heap-profiler
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_LIB_libprofiler),--enable-cpu-profiler,--disable-cpu-profiler)
$(PKG)_CONFIGURE_OPTIONS += --enable-minimal


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_TCMALLOC_MINIMAL_BINARY) $($(PKG)_PROFILER_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(GPERFTOOLS_DIR)

$($(PKG)_TCMALLOC_MINIMAL_STAGING): $($(PKG)_TCMALLOC_MINIMAL_BINARY)
	$(SUBMAKE) -C $(GPERFTOOLS_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@if [ -f "$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libtcmalloc_minimal.pc" ]; then \
		$(PKG_FIX_LIBTOOL_LA) \
			$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libtcmalloc_minimal.pc; \
	fi
	@if [ -f "$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libprofiler.pc" ]; then \
		$(PKG_FIX_LIBTOOL_LA) \
			$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libprofiler.pc; \
	fi

ifeq ($(strip $(FREETZ_LIB_libprofiler)),y)
$($(PKG)_PROFILER_STAGING): $($(PKG)_TCMALLOC_MINIMAL_STAGING)
	@test -f "$@"
endif

$($(PKG)_TCMALLOC_MINIMAL_TARGET): $($(PKG)_TCMALLOC_MINIMAL_STAGING)
	$(INSTALL_LIBRARY_STRIP)

$($(PKG)_PROFILER_TARGET): $($(PKG)_PROFILER_STAGING)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_TCMALLOC_MINIMAL_STAGING) $(if $(FREETZ_LIB_libprofiler),$($(PKG)_PROFILER_STAGING))

$(pkg)-precompiled: $($(PKG)_TCMALLOC_MINIMAL_TARGET) $(if $(FREETZ_LIB_libprofiler),$($(PKG)_PROFILER_TARGET))


$(pkg)-clean:
	-$(SUBMAKE) -C $(GPERFTOOLS_DIR) clean
	$(RM) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtcmalloc* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libprofiler* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libtcmalloc*.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libprofiler*.pc
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/gperftools

$(pkg)-uninstall:
	$(RM) \
		$(GPERFTOOLS_TARGET_DIR)/libtcmalloc*.so* \
		$(GPERFTOOLS_TARGET_DIR)/libprofiler*.so*

$(PKG_FINISH)
