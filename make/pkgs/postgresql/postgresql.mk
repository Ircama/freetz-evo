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
$(PKG)_PSQL_BINARY:=$($(PKG)_DIR)/src/bin/psql/psql
$(PKG)_TARGET_PSQL_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/psql

$(PKG)_POSTGRES_BINARY:=$($(PKG)_DIR)/src/backend/postgres
$(PKG)_PG_CTL_BINARY:=$($(PKG)_DIR)/src/bin/pg_ctl/pg_ctl
$(PKG)_INITDB_BINARY:=$($(PKG)_DIR)/src/bin/initdb/initdb
$(PKG)_TARGET_POSTGRES_BINARY:=$($(PKG)_DEST_DIR)/usr/sbin/postgres
$(PKG)_TARGET_PG_CTL_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/pg_ctl
$(PKG)_TARGET_INITDB_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/initdb

$(PKG)_TARGET_SHARE_DIR:=$($(PKG)_DEST_DIR)/usr/share/postgresql
$(PKG)_TARGET_SHARE_STAMP:=$($(PKG)_TARGET_SHARE_DIR)/.installed

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

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_POSTGRESQL
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_POSTGRESQL_SERVER


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIB_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/catalog generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/nodes generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/utils generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/interfaces/libpq

$($(PKG)_PSQL_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/catalog generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/nodes generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/utils generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/bin/psql

$($(PKG)_POSTGRES_BINARY) $($(PKG)_PG_CTL_BINARY) $($(PKG)_INITDB_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/catalog generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/nodes generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend/utils generated-header-symlinks
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend generated-headers
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/backend postgres
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/bin/pg_ctl
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/bin/initdb

$($(PKG)_TARGET_SHARE_STAMP): $($(PKG)_DIR)/.configured
	mkdir -p $(POSTGRESQL_TARGET_SHARE_DIR)
	cp $(POSTGRESQL_DIR)/src/backend/catalog/postgres.bki $(POSTGRESQL_TARGET_SHARE_DIR)/
	cp $(POSTGRESQL_DIR)/src/backend/catalog/system_constraints.sql $(POSTGRESQL_TARGET_SHARE_DIR)/
	cp $(POSTGRESQL_DIR)/src/backend/catalog/system_functions.sql $(POSTGRESQL_TARGET_SHARE_DIR)/
	cp $(POSTGRESQL_DIR)/src/backend/catalog/system_views.sql $(POSTGRESQL_TARGET_SHARE_DIR)/
	cp $(POSTGRESQL_DIR)/src/backend/catalog/information_schema.sql $(POSTGRESQL_TARGET_SHARE_DIR)/
	@touch -c $@

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_PSQL_BINARY),/usr/bin))
$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_POSTGRES_BINARY),/usr/sbin))
$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_PG_CTL_BINARY),/usr/bin))
$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_INITDB_BINARY),/usr/bin))

$($(PKG)_LIB_STAGING_DIR): $($(PKG)_LIB_BUILD_DIR)
	$(SUBMAKE) -C $(POSTGRESQL_DIR)/src/interfaces/libpq \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-lib
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libpq
	cp $(POSTGRESQL_DIR)/src/interfaces/libpq/libpq-fe.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	cp $(POSTGRESQL_DIR)/src/interfaces/libpq/libpq-events.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	cp $(POSTGRESQL_DIR)/src/include/postgres_ext.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	cp $(POSTGRESQL_PG_CONFIG_EXT_H) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/
	cp $(POSTGRESQL_DIR)/src/include/libpq/libpq-fs.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libpq/
	@touch -c $@

$($(PKG)_LIB_TARGET_DIR): $($(PKG)_LIB_STAGING_DIR)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_LIB_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_LIB_TARGET_DIR) \
	$(if $(FREETZ_PACKAGE_POSTGRESQL),$($(PKG)_TARGET_PSQL_BINARY)) \
	$(if $(FREETZ_PACKAGE_POSTGRESQL_SERVER),$($(PKG)_TARGET_POSTGRES_BINARY) $($(PKG)_TARGET_PG_CTL_BINARY) $($(PKG)_TARGET_INITDB_BINARY) $($(PKG)_TARGET_SHARE_STAMP))


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
	$(RM) \
		$(POSTGRESQL_TARGET_LIBDIR)/libpq.so* \
		$(POSTGRESQL_TARGET_PSQL_BINARY) \
		$(POSTGRESQL_TARGET_POSTGRES_BINARY) \
		$(POSTGRESQL_TARGET_PG_CTL_BINARY) \
		$(POSTGRESQL_TARGET_INITDB_BINARY)
	$(RM) -r $(POSTGRESQL_TARGET_SHARE_DIR)

$(call PKG_ADD_LIB,libpq)
$(PKG_FINISH)