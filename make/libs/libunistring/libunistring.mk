$(call PKG_INIT_LIB, 1.4)
$(PKG)_LIB_VERSION:=5.2.1
$(PKG)_SOURCE:=libunistring-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=708571fce9965e805fee08b410aa8e886d391a492c387f75abb7be0e195337f5
$(PKG)_SITE:=https://ftp.gnu.org/gnu/libunistring
### WEBSITE:=https://www.gnu.org/software/libunistring/
### MANPAGE:=https://www.gnu.org/software/libunistring/manual/
### CHANGES:=https://ftp.gnu.org/gnu/libunistring/
### CVSREPO:=https://git.savannah.gnu.org/git/libunistring.git

$(PKG)_CATEGORY_LIBS:=Charsets & Internationalization
$(PKG)_BINARY:=$($(PKG)_DIR)/lib/.libs/libunistring.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libunistring.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libunistring.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBUNISTRING_DIR)/lib

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBUNISTRING_DIR)/lib \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libunistring.la

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBUNISTRING_DIR)/lib clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libunistring* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unistring \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unitypes.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unistr.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/uniconv.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unistdio.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/uniname.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unictype.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/uniwidth.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unigbrk.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/uniwbrk.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unilbrk.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unimetadata.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/uninorm.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unicase.h

$(pkg)-uninstall:
	$(RM) $(LIBUNISTRING_TARGET_DIR)/libunistring*.so*

$(PKG_FINISH)