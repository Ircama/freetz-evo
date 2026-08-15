$(call PKG_INIT_LIB, 3.11.0)
$(PKG)_LIB_VERSION:=200.26.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=2a56e1edefa3e68a7c00879496736fdbf62fc94ed3232c0baba127ecfa76874d
$(PKG)_SITE:=https://github.com/thom311/libnl/releases/download/libnl3_11_0
### WEBSITE:=https://github.com/thom311/libnl
### MANPAGE:=https://www.infradead.org/~tgr/libnl/doc/core.html
### CHANGES:=https://github.com/thom311/libnl/releases
### CVSREPO:=https://github.com/thom311/libnl

$(PKG)_CATEGORY_LIBS:=Networking##Misc networking

$(PKG)_LIBNAMES_SHORT := nl-3 nl-cli-3 nl-genl-3 nl-nf-3 nl-route-3
$(PKG)_LIBNAMES_LONG := $($(PKG)_LIBNAMES_SHORT:%=lib%.so.$($(PKG)_LIB_VERSION))
$(PKG)_LIBS_BUILD_DIR := \
	$($(PKG)_DIR)/lib/.libs/libnl-3.so.$($(PKG)_LIB_VERSION) \
	$($(PKG)_DIR)/src/lib/.libs/libnl-cli-3.so.$($(PKG)_LIB_VERSION) \
	$($(PKG)_DIR)/lib/.libs/libnl-genl-3.so.$($(PKG)_LIB_VERSION) \
	$($(PKG)_DIR)/lib/.libs/libnl-nf-3.so.$($(PKG)_LIB_VERSION) \
	$($(PKG)_DIR)/lib/.libs/libnl-route-3.so.$($(PKG)_LIB_VERSION)
$(PKG)_LIBS_STAGING_DIR := $($(PKG)_LIBNAMES_LONG:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%)
$(PKG)_LIBS_TARGET_DIR := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_TARGET_DIR)/%)
$(PKG)_LA_STAGING_DIR := $($(PKG)_LIBNAMES_SHORT:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib%.la)
$(PKG)_PKGCONFIGS := libnl-3.0 libnl-cli-3.0 libnl-genl-3.0 libnl-nf-3.0 libnl-route-3.0

$(PKG)_CONFIGURE_OPTIONS += --enable-cli=no-inst
$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-debug


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIBS_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBNL_DIR)

$($(PKG)_LIBS_STAGING_DIR): $($(PKG)_LIBS_BUILD_DIR)
	$(SUBMAKE) -C $(LIBNL_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(LIBNL_LA_STAGING_DIR) \
		$(LIBNL_PKGCONFIGS:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/%.pc)

$($(PKG)_LIBS_TARGET_DIR): $($(PKG)_TARGET_DIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_LIBS_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_LIBS_TARGET_DIR)


$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBNL_DIR) clean
	$(RM) -r \
		$(LIBNL_LIBNAMES_SHORT:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib%*) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libnl \
		$(LIBNL_PKGCONFIGS:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/%.pc) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libnl3

$(pkg)-uninstall:
	$(RM) $(LIBNL_LIBNAMES_SHORT:%=$(LIBNL_TARGET_DIR)/lib%.so*)

$(PKG_FINISH)
