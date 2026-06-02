$(call PKG_INIT_LIB, 0.81)
$(PKG)_LIB_VERSION:=1
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=469de2d445bf54880f652f4b6dc95c7cdf6f5502c35524a45b2122d70d47ebc2
$(PKG)_SITE:=https://www.corpit.ru/mjt/tinycdb
### WEBSITE:=https://www.corpit.ru/mjt/tinycdb.html

$(PKG)_BINARY:=$($(PKG)_DIR)/libcdb.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcdb.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libcdb.so.$($(PKG)_LIB_VERSION)
$(PKG)_PC_FILE:=$($(PKG)_DIR)/libcdb.pc

$(PKG)_COMMON_MAKE_OPTS := -C $($(PKG)_DIR)
$(PKG)_COMMON_MAKE_OPTS += CC="$(TARGET_CC)"
$(PKG)_COMMON_MAKE_OPTS += LD="$(TARGET_CC)"
$(PKG)_COMMON_MAKE_OPTS += AR="$(TARGET_AR)"
$(PKG)_COMMON_MAKE_OPTS += RANLIB="$(TARGET_RANLIB)"
$(PKG)_COMMON_MAKE_OPTS += CFLAGS="$(TARGET_CFLAGS)"
$(PKG)_COMMON_MAKE_OPTS += LDFLAGS="$(TARGET_LDFLAGS)"
$(PKG)_COMMON_MAKE_OPTS += prefix="/usr"
$(PKG)_COMMON_MAKE_OPTS += libdir="/usr/lib"
$(PKG)_COMMON_MAKE_OPTS += pkgconfdir="/usr/lib/pkgconfig"
$(PKG)_COMMON_MAKE_OPTS += includedir="/usr/include"


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_BINARY): $($(PKG)_DIR)/.unpacked
	$(SUBMAKE) $(TINYCDB_COMMON_MAKE_OPTS) sharedlib libcdb.pc

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) $(TINYCDB_COMMON_MAKE_OPTS) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-sharedlib
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/; \
	cp $(TINYCDB_DIR)/cdb.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/; \
	cp $(TINYCDB_PC_FILE) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) $(TINYCDB_COMMON_MAKE_OPTS) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcdb.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libcdb.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/cdb.h

$(pkg)-uninstall:
	$(RM) $(TINYCDB_TARGET_DIR)/libcdb.so*

$(PKG_FINISH)