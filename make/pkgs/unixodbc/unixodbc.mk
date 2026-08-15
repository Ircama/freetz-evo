$(call PKG_INIT_BIN, 2.3.12)
$(PKG)_LIB_VERSION:=2.0.0
$(PKG)_SOURCE_DOWNLOAD_NAME:=unixODBC-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f210501445ce21bf607ba51ef8c125e10e22dffdffec377646462df5f01915ec
$(PKG)_SITE:=http://www.unixodbc.org
### WEBSITE:=https://www.unixodbc.org/
### CHANGES:=https://github.com/lurcher/unixODBC/releases
### CVSREPO:=https://github.com/lurcher/unixODBC

$(PKG)_CATEGORY_LIBS:=Database

$(PKG)_LIBS_ALL := libodbc.so.$($(PKG)_LIB_VERSION) libodbcinst.so.$($(PKG)_LIB_VERSION) libodbccr.so.$($(PKG)_LIB_VERSION)
$(PKG)_LIBS := $(if $(FREETZ_LIB_libodbc),libodbc.so.$($(PKG)_LIB_VERSION)) $(if $(FREETZ_LIB_libodbcinst),libodbcinst.so.$($(PKG)_LIB_VERSION)) $(if $(FREETZ_LIB_libodbccr),libodbccr.so.$($(PKG)_LIB_VERSION))

$(PKG)_LIBS_BUILD_DIR := \
	$($(PKG)_DIR)/DriverManager/.libs/libodbc.so.$($(PKG)_LIB_VERSION) \
	$($(PKG)_DIR)/odbcinst/.libs/libodbcinst.so.$($(PKG)_LIB_VERSION) \
	$($(PKG)_DIR)/cur/.libs/libodbccr.so.$($(PKG)_LIB_VERSION)
$(PKG)_LIBS_STAGING_DIR := $(addprefix $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/,$($(PKG)_LIBS))
$(PKG)_LIBS_TARGET_DIR := $(addprefix $($(PKG)_TARGET_LIBDIR)/,$($(PKG)_LIBS))

$(PKG)_BINARIES := isql iusql odbcinst
$(PKG)_BINARIES_STAGING_DIR := $(addprefix $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/,$($(PKG)_BINARIES))
$(PKG)_BINARIES_TARGET_DIR := $(addprefix $($(PKG)_DEST_DIR)/usr/bin/,$($(PKG)_BINARIES))

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libodbc
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libodbcinst
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libodbccr
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_UNIXODBC

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)
$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --enable-drivers=no
$(PKG)_CONFIGURE_OPTIONS += --enable-gui=no
$(PKG)_CONFIGURE_OPTIONS += --enable-iconv=no
$(PKG)_CONFIGURE_OPTIONS += --enable-readline=no
$(PKG)_CONFIGURE_OPTIONS += --with-included-ltdl


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIBS_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(UNIXODBC_DIR)

$($(PKG)_LIBS_STAGING_DIR): $($(PKG)_LIBS_BUILD_DIR)
	$(SUBMAKE) -C $(UNIXODBC_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libodbc*.la \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/{odbc,odbcinst,odbccr}.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/odbc_config
	@touch -c $@

$($(PKG)_LIBS_TARGET_DIR): $($(PKG)_TARGET_LIBDIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(foreach binary,$($(PKG)_BINARIES_STAGING_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/bin)))

$(pkg): $($(PKG)_LIBS_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_LIBS_TARGET_DIR) $(if $(FREETZ_PACKAGE_UNIXODBC),$($(PKG)_BINARIES_TARGET_DIR))


$(pkg)-clean:
	-$(SUBMAKE) -C $(UNIXODBC_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/{dltest,isql,iusql,odbc_config,odbcinst,slencheck} \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/{odbcinst.h,odbcinstext.h,uodbc_extras.h,uodbc_stats.h,sql.h,sqlext.h,sqlspi.h,sqltypes.h,sqlucode.h,unixodbc.h} \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libodbc* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libodbccr* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/{odbc,odbcinst,odbccr}.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/man/man1/{dltest,isql,iusql,odbc_config,odbcinst}.1 \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/man/man5/{odbc.ini,odbcinst.ini}.5 \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/etc/odbc*.ini

$(pkg)-uninstall:
	$(RM) $(UNIXODBC_TARGET_LIBDIR)/libodbc*.so* $(UNIXODBC_TARGET_LIBDIR)/libodbccr*.so* $(UNIXODBC_DEST_DIR)/usr/bin/{isql,iusql,odbcinst}

$(call PKG_ADD_LIB,libodbc)
$(call PKG_ADD_LIB,libodbcinst)
$(call PKG_ADD_LIB,libodbccr)
$(PKG_FINISH)