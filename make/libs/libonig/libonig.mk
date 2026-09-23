$(call PKG_INIT_LIB, 6.9.10)
$(PKG)_LIB_VERSION:=5.5.0
$(PKG)_SOURCE:=onig-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=2a5cfc5ae259e4e97f86b68dfffc152cdaffe94e2060b770cb827238d769fc05
$(PKG)_SITE:=https://github.com/kkos/oniguruma/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://github.com/kkos/oniguruma/blob/master/README.md
### MANPAGE:=https://github.com/kkos/oniguruma/blob/master/README.md#usage
### CHANGES:=https://github.com/kkos/oniguruma/releases
### CVSREPO:=https://github.com/kkos/oniguruma

$(PKG)_CATEGORY_LIBS:=Regular expressions

$(PKG)_LIBBASE:=libonig.so
$(PKG)_LIBNAME:=$($(PKG)_LIBBASE).$($(PKG)_LIB_VERSION)
$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/$($(PKG)_LIBNAME)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/$($(PKG)_LIBNAME)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/$($(PKG)_LIBNAME)

$(PKG)_PATCH_POST_CMDS += $(RM) compile config.guess config.sub depcomp install-sh missing test-driver;
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBONIG_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBONIG_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-strip
	$(SUBMAKE) -C $(LIBONIG_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-pkgconfigDATA
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libonig.la \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/oniguruma.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/onig-config

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBONIG_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libonig* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/oniguruma.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/oniggnu.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/onigposix.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/onig-config

$(pkg)-uninstall:
	$(RM) $(LIBONIG_TARGET_DIR)/$(LIBONIG_LIBBASE)*

$(PKG_FINISH)
