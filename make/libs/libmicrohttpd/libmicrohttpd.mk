$(call PKG_INIT_LIB, 0.9.77)
$(PKG)_LIB_VERSION:=12.61.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=9e7023a151120060d2806a6ea4c13ca9933ece4eacfc5c9464d20edddb76b0a0
$(PKG)_SITE:=https://ftp.gnu.org/gnu/libmicrohttpd
### WEBSITE:=https://www.gnu.org/software/libmicrohttpd/
### CHANGES:=https://ftp.gnu.org/gnu/libmicrohttpd/

$(PKG)_BINARY:=$($(PKG)_DIR)/src/microhttpd/.libs/libmicrohttpd.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmicrohttpd.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libmicrohttpd.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-nls
$(PKG)_CONFIGURE_OPTIONS += --disable-doc
$(PKG)_CONFIGURE_OPTIONS += --disable-examples
$(PKG)_CONFIGURE_OPTIONS += --disable-curl
$(PKG)_CONFIGURE_OPTIONS += --disable-messages
$(PKG)_CONFIGURE_OPTIONS += --disable-postprocessor
$(PKG)_CONFIGURE_OPTIONS += --disable-bauth
$(PKG)_CONFIGURE_OPTIONS += --disable-dauth
$(PKG)_CONFIGURE_OPTIONS += --disable-httpupgrade
$(PKG)_CONFIGURE_OPTIONS += --enable-https=no
$(PKG)_CONFIGURE_OPTIONS += --enable-poll=auto
$(PKG)_CONFIGURE_OPTIONS += --enable-epoll=auto
$(PKG)_CONFIGURE_OPTIONS += --disable-largefile


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBMICROHTTPD_DIR) all

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBMICROHTTPD_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmicrohttpd* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/microhttpd.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libmicrohttpd*.pc

$(pkg)-uninstall:
	$(RM) $(LIBMICROHTTPD_TARGET_DIR)/libmicrohttpd*.so*

$(PKG_FINISH)
