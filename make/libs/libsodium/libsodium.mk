$(call PKG_INIT_LIB, 1.0.20)
$(PKG)_LIB_VERSION:=26.2.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ebb65ef6ca439333c2bb41a0c1990587288da07f6c7fd07cb3a18cc18d30ce19
$(PKG)_SITE:=https://download.libsodium.org/libsodium/releases
### WEBSITE:=https://libsodium.org/
### CHANGES:=https://github.com/jedisct1/libsodium/releases
### CVSREPO:=https://github.com/jedisct1/libsodium

$(PKG)_CATEGORY_LIBS:=Crypto & SSL##Misc
$(PKG)_BINARY:=$($(PKG)_DIR)/src/libsodium/.libs/libsodium.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libsodium.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libsodium.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)
$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBSODIUM_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBSODIUM_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libsodium.la \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libsodium.pc

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

# Ensure libsodium.pc exists even if staging binary is up-to-date
$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libsodium.pc:
	@mkdir -p $(dir $@)
	echo -ne \
		"prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr\n"\
		"exec_prefix=\$${prefix}\n"\
		"libdir=\$${prefix}/lib\n"\
		"includedir=\$${prefix}/include\n"\
		"\n"\
		"Name: libsodium\n"\
		"Version: $(LIBSODIUM_VERSION)\n"\
		"Description: libsodium is a portable, cross-compilable, installable, packageable, fork of NaCl\n"\
		"URL: https://libsodium.org\n"\
		"Libs: -L\$${libdir} -lsodium\n"\
		"Libs.private: -lm\n"\
		"Cflags: -I\$${includedir}\n"\
		>$@

$(pkg): $($(PKG)_STAGING_BINARY) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libsodium.pc

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBSODIUM_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libsodium* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libsodium.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/sodium \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/sodium.h

$(pkg)-uninstall:
	$(RM) $(LIBSODIUM_TARGET_DIR)/libsodium.so*

$(PKG_FINISH)