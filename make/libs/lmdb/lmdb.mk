$(call PKG_INIT_LIB, 0.9.33)
$(PKG)_SOURCE_DOWNLOAD_NAME:=LMDB_$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=9c352fa9bdad53d920128ac6a62296f2850c7e29862a610d3a72f5f49a1cd7ea
$(PKG)_SITE:=https://github.com/LMDB/lmdb/archive/refs/tags
### WEBSITE:=https://www.symas.com/lmdb/
### CHANGES:=https://github.com/LMDB/lmdb/releases
### CVSREPO:=https://github.com/LMDB/lmdb

$(PKG)_BINARY:=$($(PKG)_DIR)/libraries/liblmdb/liblmdb.so
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblmdb.so
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/liblmdb.so
$(PKG)_PC_FILE:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/lmdb.pc

$(PKG)_COMMON_MAKE_OPTS := -C $($(PKG)_DIR)/libraries/liblmdb
$(PKG)_COMMON_MAKE_OPTS += CC="$(TARGET_CC)"
$(PKG)_COMMON_MAKE_OPTS += AR="$(TARGET_AR)"
$(PKG)_COMMON_MAKE_OPTS += XCFLAGS="$(TARGET_CFLAGS) -fPIC"
$(PKG)_COMMON_MAKE_OPTS += CPPFLAGS="$(TARGET_CPPFLAGS)"
$(PKG)_COMMON_MAKE_OPTS += LDFLAGS="$(TARGET_LDFLAGS)"
$(PKG)_COMMON_MAKE_OPTS += prefix="/usr"
$(PKG)_COMMON_MAKE_OPTS += bindir="/usr/bin"
$(PKG)_COMMON_MAKE_OPTS += libdir="/usr/lib"
$(PKG)_COMMON_MAKE_OPTS += includedir="/usr/include"


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_BINARY): $($(PKG)_DIR)/.unpacked
	$(SUBMAKE) $(LMDB_COMMON_MAKE_OPTS) liblmdb.so

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) $(LMDB_COMMON_MAKE_OPTS) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		ILIBS="liblmdb.so" \
		IPROGS="" \
		IDOCS="" \
		install
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig
	printf '%s\n' 'prefix=/usr' > $(LMDB_PC_FILE)
	printf '%s\n' 'exec_prefix=$${prefix}' >> $(LMDB_PC_FILE)
	printf '%s\n' 'libdir=$${exec_prefix}/lib' >> $(LMDB_PC_FILE)
	printf '%s\n' 'includedir=$${prefix}/include' >> $(LMDB_PC_FILE)
	printf '%s\n' '' >> $(LMDB_PC_FILE)
	printf '%s\n' 'Name: lmdb' >> $(LMDB_PC_FILE)
	printf '%s\n' 'Description: Lightning Memory-Mapped Database library' >> $(LMDB_PC_FILE)
	printf '%s\n' 'Version: $(LMDB_VERSION)' >> $(LMDB_PC_FILE)
	printf '%s\n' 'Libs: -L$${libdir} -llmdb' >> $(LMDB_PC_FILE)
	printf '%s\n' 'Cflags: -I$${includedir}' >> $(LMDB_PC_FILE)

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) $(LMDB_COMMON_MAKE_OPTS) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblmdb.so \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/lmdb.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/lmdb.h

$(pkg)-uninstall:
	$(RM) $(LMDB_TARGET_DIR)/liblmdb.so

$(PKG_FINISH)