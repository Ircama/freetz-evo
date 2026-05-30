$(call PKG_INIT_BIN, 16.3)
$(PKG)_LIB_VERSION:=5.16
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=bd3798c399bc1b6d08b94340f9dd7a75a30a7fa076788ef2f4848be2be6a5fc5
$(PKG)_SITE:=https://ftp.postgresql.org/pub/source/v$($(PKG)_VERSION)
### WEBSITE:=https://www.postgresql.org/
### CHANGES:=https://www.postgresql.org/docs/release/
### CVSREPO:=https://git.postgresql.org/gitweb/?p=postgresql.git

$(PKG)_LIB:=libpq.so.$($(PKG)_LIB_VERSION)
$(PKG)_LIB_BUILD_DIR:=$($(PKG)_DIR)/src/interfaces/libpq/$($(PKG)_LIB)
$(PKG)_LIB_STAGING_DIR:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/$($(PKG)_LIB)
$(PKG)_LIB_TARGET_DIR:=$($(PKG)_TARGET_LIBDIR)/$($(PKG)_LIB)
$(PKG)_PG_CONFIG_EXT_H:=$($(PKG)_DIR)/src/include/pg_config_ext.h

$(PKG)_CONFIGURE_OPTIONS += --disable-nls
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --with-openssl=no
$(PKG)_CONFIGURE_OPTIONS += --without-gssapi
$(PKG)_CONFIGURE_OPTIONS += --without-icu
$(PKG)_CONFIGURE_OPTIONS += --without-ldap
$(PKG)_CONFIGURE_OPTIONS += --without-libxml
$(PKG)_CONFIGURE_OPTIONS += --without-libxslt
$(PKG)_CONFIGURE_OPTIONS += --without-readline
$(PKG)_CONFIGURE_OPTIONS += --without-zlib


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIB_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/interfaces/libpq

$($(PKG)_LIB_STAGING_DIR): $($(PKG)_LIB_BUILD_DIR)
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/interfaces/libpq \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-lib
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libpq
	$(INSTALL_FILE) $(POSTGRESQL_DIR)/src/interfaces/libpq/libpq-fe.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	$(INSTALL_FILE) $(POSTGRESQL_DIR)/src/interfaces/libpq/libpq-events.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	$(INSTALL_FILE) $(POSTGRESQL_DIR)/src/include/postgres_ext.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	$(INSTALL_FILE) $(POSTGRESQL_PG_CONFIG_EXT_H) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	$(INSTALL_FILE) $(POSTGRESQL_DIR)/src/include/libpq/libpq-fs.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libpq/
	@touch -c $@

$($(PKG)_LIB_TARGET_DIR): $($(PKG)_LIB_STAGING_DIR)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_LIB_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_LIB_TARGET_DIR)


$(pkg)-clean:
	-$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/interfaces/libpq clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libpq* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libpq.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libpq-fe.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libpq-events.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/postgres_ext.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/pg_config_ext.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libpq/

$(pkg)-uninstall:
	$(RM) $(POSTGRESQL_TARGET_LIBDIR)/libpq.so*

$(call PKG_ADD_LIB,libpq)
$(PKG_FINISH)