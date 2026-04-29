$(call PKG_INIT_BIN, 1.37.0)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=60a420ad7085eb616cb6e2bdf0a7206d68ff3d37fb5a956dc44242eb2f79b66b
$(PKG)_SITE:=https://github.com/aria2/aria2/releases/download/release-$($(PKG)_VERSION)
### WEBSITE:=https://aria2.github.io/
### MANPAGE:=https://aria2.github.io/manual/en/html/
### CHANGES:=https://github.com/aria2/aria2/releases
### CVSREPO:=https://github.com/aria2/aria2.git
### SUPPORT:=Ircama
### STEWARD:=Ircama

$(PKG)_BINARIES := aria2c
# aria2 uses libtool; src/aria2c is a shell wrapper and the real ELF is in src/.libs/aria2c
$(PKG)_BINARIES_BUILD_DIR := $($(PKG)_DIR)/src/.libs/aria2c
$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_DEST_DIR)/usr/bin/aria2c

$(PKG)_LIB_VERSION := 0.0.0
$(PKG)_LIBNAMES_SHORT := aria2
$(PKG)_LIBNAMES_LONG := $($(PKG)_LIBNAMES_SHORT:%=lib%.so.$($(PKG)_LIB_VERSION))
$(PKG)_LIBS_BUILD_DIR := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_DIR)/src/.libs/%)
$(PKG)_LIBS_STAGING_DIR := $($(PKG)_LIBNAMES_LONG:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%)
$(PKG)_LIBS_TARGET_DIR := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_TARGET_LIBDIR)/%)

# Base dependencies (always required)
$(PKG)_DEPENDS_ON += zlib

# Conditional dependencies - defined separately for clarity
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_OPENSSL)),y)
$(PKG)_DEPENDS_ON += openssl
endif

ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_GNUTLS)),y)
$(PKG)_DEPENDS_ON += gnutls
endif

ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_BITTORRENT)),y)
$(PKG)_DEPENDS_ON += nettle
$(PKG)_DEPENDS_ON += gmp
endif

# XML parser dependency - required by XML-RPC or Metalink
ifneq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_XMLRPC)$(FREETZ_PACKAGE_ARIA2_WITH_METALINK)),)
$(PKG)_DEPENDS_ON += libxml2
endif

ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_LIBSSH2)),y)
$(PKG)_DEPENDS_ON += libssh2
endif

# libcares: Only if async DNS is enabled
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITHOUT_ASYNC_DNS)),)
$(PKG)_DEPENDS_ON += libcares
endif

# jemalloc (required to avoid SIGFPE with uClibc 1.0.57 when running aria2c):
$(PKG)_DEPENDS_ON += jemalloc

$(PKG)_DEPENDS_ON += $(STDCXXLIB)

# Track options that affect rebuild
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_OPENSSL
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_GNUTLS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_BITTORRENT
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_METALINK
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_XMLRPC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_WEBSOCKET
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_LIBSSH2
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_SQLITE3
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITHOUT_ASYNC_DNS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_STATIC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ARIA2_WITH_LIBARIA2
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libaria2
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_legacy

# Determine SSL library
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_OPENSSL)),y)
ARIA2_SSL_LIB := openssl
else
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_GNUTLS)),y)
ARIA2_SSL_LIB := gnutls
else
ARIA2_SSL_LIB := openssl
endif
endif

# Keep upstream configure script to avoid accidental host-tool leakage from
# local autotools regeneration during cross-compilation.
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

# Configure options - base settings
$(PKG)_CONFIGURE_OPTIONS += --with-libuv=no
$(PKG)_CONFIGURE_OPTIONS += --without-appletls
$(PKG)_CONFIGURE_OPTIONS += --without-wintls
$(PKG)_CONFIGURE_OPTIONS += --without-libgcrypt
$(PKG)_CONFIGURE_OPTIONS += --without-tcmalloc
$(PKG)_CONFIGURE_OPTIONS += --with-jemalloc

# Async DNS (libcares) support
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITHOUT_ASYNC_DNS)),y)
$(PKG)_CONFIGURE_OPTIONS += --without-libcares
else
$(PKG)_CONFIGURE_OPTIONS += --with-libcares
endif

# BitTorrent support
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_BITTORRENT)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-bittorrent
$(PKG)_CONFIGURE_OPTIONS += --with-libnettle
$(PKG)_CONFIGURE_OPTIONS += --with-libgmp
else
$(PKG)_CONFIGURE_OPTIONS += --disable-bittorrent
$(PKG)_CONFIGURE_OPTIONS += --without-libnettle
$(PKG)_CONFIGURE_OPTIONS += --without-libgmp
endif

# Metalink support
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_METALINK)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-metalink
else
$(PKG)_CONFIGURE_OPTIONS += --disable-metalink
endif

# XML-RPC support
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_XMLRPC)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-xml-rpc
else
$(PKG)_CONFIGURE_OPTIONS += --disable-xml-rpc
endif

# XML parser (libxml2) - required by XML-RPC or Metalink
ifneq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_XMLRPC)$(FREETZ_PACKAGE_ARIA2_WITH_METALINK)),)
$(PKG)_CONFIGURE_OPTIONS += --with-libxml2
else
$(PKG)_CONFIGURE_OPTIONS += --without-libxml2
$(PKG)_CONFIGURE_OPTIONS += --without-libexpat
endif

# WebSocket support
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_WEBSOCKET)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-websocket
else
$(PKG)_CONFIGURE_OPTIONS += --disable-websocket
endif

# SFTP/SCP support
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_LIBSSH2)),y)
$(PKG)_CONFIGURE_OPTIONS += --with-libssh2
else
$(PKG)_CONFIGURE_OPTIONS += --without-libssh2
endif

# Cookie support (Firefox3/Chromium)
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_WITH_SQLITE3)),y)
$(PKG)_DEPENDS_ON += sqlite
$(PKG)_CONFIGURE_OPTIONS += --with-sqlite3
else
$(PKG)_CONFIGURE_OPTIONS += --without-sqlite3
endif

# SSL/TLS configuration
ifeq ($(ARIA2_SSL_LIB),openssl)
$(PKG)_CONFIGURE_OPTIONS += --with-openssl
$(PKG)_CONFIGURE_OPTIONS += --without-gnutls
$(PKG)_CONFIGURE_OPTIONS += --with-ca-bundle=/etc/ssl/certs/ca-bundle.crt
$(PKG)_CONFIGURE_ENV += OPENSSL_CFLAGS="-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_ENV += OPENSSL_LIBS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -lssl -lcrypto"
else ifeq ($(ARIA2_SSL_LIB),gnutls)
$(PKG)_CONFIGURE_OPTIONS += --with-gnutls
$(PKG)_CONFIGURE_OPTIONS += --without-openssl
$(PKG)_CONFIGURE_OPTIONS += --with-ca-bundle=/etc/ssl/certs/ca-bundle.crt
$(PKG)_CONFIGURE_ENV += GNUTLS_CFLAGS="-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_ENV += GNUTLS_LIBS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -lgnutls"
endif

# libaria2 C++ library support
ifeq ($(strip $(FREETZ_LIB_libaria2)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-libaria2
# --enable-static overrides LT_INIT([disable-static]) in configure.ac
# so that libtool builds libaria2.a.
$(PKG)_CONFIGURE_OPTIONS += --enable-static
else
$(PKG)_CONFIGURE_OPTIONS += --disable-libaria2
endif

# Extra compilation flags for optimization and size reduction.
# NOTE: $(PKG)_EXTRA_CFLAGS/EXTRA_LDFLAGS are only injected via %TARGET_CFLAGS%
# placeholders in meson.cross files, not for autoconf packages whose CONFIGURE_ENV
# explicitly overrides CFLAGS/CXXFLAGS/LDFLAGS. Fold them directly here.
ARIA2_EXTRA_CFLAGS  := -ffunction-sections -fdata-sections
ARIA2_EXTRA_LDFLAGS := -Wl,--gc-sections

# Jemalloc is mandatory
ARIA2_EXTRA_LDFLAGS += -L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -ljemalloc

# TARGET_CFLAGS includes --std=gnu99 (TARGET_CFLAGS_GCC) — valid for CC but not
# for CXX; filter it out to keep CXXFLAGS clean.
ARIA2_CXXFLAGS := $(filter-out --std=gnu99 -std=gnu99,$(TARGET_CFLAGS))

# Force C++11 support (aria2 requires C++11)
$(PKG)_CONFIGURE_ENV += CXX="$(TARGET_TOOLCHAIN_STAGING_DIR)/bin/$(REAL_GNU_TARGET_NAME)-g++"
$(PKG)_CONFIGURE_ENV += CFLAGS="$(TARGET_CFLAGS) $(ARIA2_EXTRA_CFLAGS)"
$(PKG)_CONFIGURE_ENV += CXXFLAGS="$(ARIA2_CXXFLAGS) $(ARIA2_EXTRA_CFLAGS) -std=c++11"
$(PKG)_CONFIGURE_ENV += LDFLAGS="$(ARIA2_EXTRA_LDFLAGS)"

# Static linking option — use ARIA2_STATIC env var (supported by aria2 configure)
# and also pass -all-static directly in LDFLAGS since EXTRA_LDFLAGS is dead for
# autoconf packages that explicitly set LDFLAGS in CONFIGURE_ENV.
ifeq ($(strip $(FREETZ_PACKAGE_ARIA2_STATIC)),y)
$(PKG)_CONFIGURE_ENV += ARIA2_STATIC=yes
$(PKG)_CONFIGURE_ENV += LDFLAGS="$(ARIA2_EXTRA_LDFLAGS) -all-static"
endif

# Shorthand variable for recipe expansion
ARIA2_DIR:=$($(PKG)_DIR)

# Standard build targets
$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

# Build targets
ifeq ($(strip $(FREETZ_LIB_libaria2)),y)
$($(PKG)_LIBS_BUILD_DIR) $($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(ARIA2_DIR)
else
$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(ARIA2_DIR)
endif

# Binary target
$($(PKG)_BINARIES_TARGET_DIR): $($(PKG)_BINARIES_BUILD_DIR)
	$(INSTALL_BINARY_STRIP)
ifeq ($(strip $(FREETZ_LIB_libaria2)),y)
	# Fix host staging RPATH baked in by libtool; on the device only /usr/lib/freetz exists
	patchelf-target --set-rpath $(FREETZ_LIBRARY_DIR) $@
endif

ifeq ($(strip $(FREETZ_LIB_libaria2)),y)
# Library staging target
$($(PKG)_LIBS_STAGING_DIR): $($(PKG)_LIBS_BUILD_DIR)
	$(SUBMAKE) -C $(ARIA2_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-strip
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libaria2.pc

# Library target
# Note: libtool install-strip rewrites RPATH to the host staging libdir
$($(PKG)_LIBS_TARGET_DIR): $($(PKG)_TARGET_LIBDIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP)
	patchelf-target --set-rpath $(FREETZ_LIBRARY_DIR) $@

$(pkg): $($(PKG)_LIBS_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR) $($(PKG)_LIBS_TARGET_DIR)
else

$(pkg): $($(PKG)_BINARIES_BUILD_DIR)

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)
endif

$(pkg)-clean:
	-$(SUBMAKE) -C $(ARIA2_DIR) clean
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libaria2* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libaria2.pc
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/aria2

$(pkg)-uninstall:
	$(RM) \
		$($(PKG)_BINARIES_TARGET_DIR) \
		$($(PKG)_TARGET_LIBDIR)/libaria2.so*

$(call PKG_ADD_LIB,libaria2)
$(PKG_FINISH)
