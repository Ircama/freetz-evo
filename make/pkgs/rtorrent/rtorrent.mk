$(call PKG_INIT_BIN, 0.16.10)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ee3cbd8ee95d98b266f6dbef56ce6b566d340955c762dc4c407f45b706ff5733
$(PKG)_SITE:=https://github.com/rakshasa/rtorrent/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://github.com/rakshasa/rtorrent
### MANPAGE:=https://github.com/rakshasa/rtorrent/wiki
### CHANGES:=https://github.com/rakshasa/rtorrent/releases
### CVSREPO:=https://github.com/rakshasa/rtorrent
### SUPPORT:=Ircama

# libTorrent by rakshasa
# (distinct from libtorrent-rasterbar used by qBittorrent/Deluge)
LIBTORRENT_RAKSHASA_VERSION:=0.16.10
LIBTORRENT_SOURCE:=libtorrent-$(LIBTORRENT_RAKSHASA_VERSION).tar.gz
LIBTORRENT_HASH:=c707c7eeea2e969e6a16ffed6b5b1e92bb94a75e97c81cc3d0aba7867f652386
LIBTORRENT_SITE:=https://github.com/rakshasa/rtorrent/releases/download/v$(LIBTORRENT_RAKSHASA_VERSION)
LIBTORRENT_DIR:=$(SOURCE_DIR)/libtorrent-$(LIBTORRENT_RAKSHASA_VERSION)

$(PKG)_BINARY:=$($(PKG)_DIR)/src/rtorrent
$(PKG)_BINARY_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/rtorrent

LIBTORRENT_BINARY:=$(LIBTORRENT_DIR)/src/.libs/libtorrent.so
LIBTORRENT_STAGING_LIB:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtorrent.so
LIBTORRENT_TARGET_LIB:=$($(PKG)_DEST_DIR)/usr/lib/freetz/libtorrent.so

$(PKG)_DEPENDS_ON += curl openssl zlib ncurses expat

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RTORRENT_STATIC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RTORRENT_WITH_IPV6
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RTORRENT_WITH_XMLRPC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RTORRENT_DAEMON

$(PKG)_CONFIGURE_OPTIONS += --host=$(GNU_TARGET_NAME)
$(PKG)_CONFIGURE_OPTIONS += --build=$(GNU_HOST_NAME)
$(PKG)_CONFIGURE_OPTIONS += --prefix=/usr
$(PKG)_CONFIGURE_OPTIONS += --with-ncurses
$(PKG)_CONFIGURE_OPTIONS += --enable-static=$(if $(FREETZ_PACKAGE_RTORRENT_STATIC),yes,no)
$(PKG)_CONFIGURE_OPTIONS += --enable-shared=$(if $(FREETZ_PACKAGE_RTORRENT_STATIC),no,yes)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_RTORRENT_WITH_IPV6),--enable-ipv6,--disable-ipv6)
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_RTORRENT_WITH_XMLRPC),--with-xmlrpc-c)

LIBTORRENT_CONFIGURE_OPTIONS := --host=$(GNU_TARGET_NAME)
LIBTORRENT_CONFIGURE_OPTIONS += --build=$(GNU_HOST_NAME)
LIBTORRENT_CONFIGURE_OPTIONS += --prefix=/usr
LIBTORRENT_CONFIGURE_OPTIONS += --enable-static=$(if $(FREETZ_PACKAGE_RTORRENT_STATIC),yes,no)
LIBTORRENT_CONFIGURE_OPTIONS += --enable-shared=$(if $(FREETZ_PACKAGE_RTORRENT_STATIC),no,yes)
LIBTORRENT_CONFIGURE_OPTIONS += --disable-instrumentation
LIBTORRENT_CONFIGURE_OPTIONS += --enable-aligned

# Intermediate variables to avoid double expansion in shell commands
RTORRENT_PKG_DIR := $($(PKG)_DIR)
RTORRENT_PKG_CONFIGURE_OPTIONS := $($(PKG)_CONFIGURE_OPTIONS)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# Download additional sources
$(DL_DIR)/libtorrent-$(LIBTORRENT_RAKSHASA_VERSION).tar.gz:
	$(DL_TOOL) $(DL_DIR) libtorrent-$(LIBTORRENT_RAKSHASA_VERSION).tar.gz $(LIBTORRENT_SITE) $(LIBTORRENT_HASH)

# Build libtorrent
$(LIBTORRENT_BINARY): $(DL_DIR)/libtorrent-$(LIBTORRENT_RAKSHASA_VERSION).tar.gz
	$(call UNPACK_TARBALL,$<,$(SOURCE_DIR))
	@echo ">>> Building libtorrent in $(LIBTORRENT_DIR)" $(SILENT)
	(cd $(LIBTORRENT_DIR) && \
		$(TARGET_CONFIGURE_ENV) \
		AR="$(TARGET_AR)" \
		RANLIB="$(TARGET_RANLIB)" \
		CPPFLAGS="-DOPENSSL_API_COMPAT=0x10100000L -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include" \
		LDFLAGS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib" \
		./configure \
			$(LIBTORRENT_CONFIGURE_OPTIONS) && \
		$(MAKE1) && \
		: \
	)

$(LIBTORRENT_STAGING_LIB): $(LIBTORRENT_BINARY)
	$(SUBMAKE) -C $(LIBTORRENT_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtorrent.la

$(LIBTORRENT_TARGET_LIB): $(LIBTORRENT_STAGING_LIB)
	$(INSTALL_LIBRARY_STRIP)

# Build rTorrent
ifeq ($(strip $(FREETZ_PACKAGE_RTORRENT_DAEMON)),y)
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked $(LIBTORRENT_STAGING_LIB)
	@echo ">>> Building rTorrent in $(RTORRENT_PKG_DIR)" $(SILENT)
	(cd $(RTORRENT_PKG_DIR) && \
		$(TARGET_CONFIGURE_ENV) \
		AR="$(TARGET_AR)" \
		RANLIB="$(TARGET_RANLIB)" \
		CPPFLAGS="-DOPENSSL_API_COMPAT=0x10100000L -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include" \
		CFLAGS="$(TARGET_CFLAGS) -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include" \
		CXXFLAGS="$(TARGET_CFLAGS) -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include" \
		LDFLAGS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib" \
		PKG_CONFIG_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig:$(TARGET_MAKE_PATH)/../lib/pkgconfig" \
		PKG_CONFIG_LIBDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig:$(TARGET_MAKE_PATH)/../lib/pkgconfig" \
		XMLRPC_C_CONFIG="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/xmlrpc-c-config" \
		./configure \
			$(RTORRENT_PKG_CONFIGURE_OPTIONS) \
	) $(SILENT)
	touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(RTORRENT_PKG_DIR)

$($(PKG)_BINARY_TARGET): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)
endif

$(pkg):

$(pkg)-precompiled: \
	$(if $(FREETZ_PACKAGE_RTORRENT_DAEMON),$($(PKG)_BINARY_TARGET)) \
	$(if $(FREETZ_PACKAGE_RTORRENT_STATIC),,$(LIBTORRENT_TARGET_LIB))

$(pkg)-clean:
	-[ -d $(LIBTORRENT_DIR) ] && $(MAKE) -C $(LIBTORRENT_DIR) clean $(SILENT)
	-[ -d $(RTORRENT_PKG_DIR) ] && $(MAKE) -C $(RTORRENT_PKG_DIR) clean $(SILENT)
	$(RM) -rf \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtorrent* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/torrent \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libtorrent.pc

$(pkg)-uninstall:
	$(RM) $($(PKG)_BINARY_TARGET)
	$(RM) $(LIBTORRENT_TARGET_LIB)

$(PKG_FINISH)
