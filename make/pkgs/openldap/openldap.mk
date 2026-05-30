$(call PKG_INIT_BIN, 2.6.8)
$(PKG)_LIB_VERSION:=2.200.0
$(PKG)_SOURCE:=openldap-$($(PKG)_VERSION).tgz
$(PKG)_HASH:=48969323e94e3be3b03c6a132942dcba7ef8d545f2ad35401709019f696c3c4e
$(PKG)_SITE:=https://www.openldap.org/software/download/OpenLDAP/openldap-release
### WEBSITE:=https://www.openldap.org/
### CHANGES:=https://www.openldap.org/software/release/changes.html
### CVSREPO:=https://git.openldap.org/openldap/openldap

$(PKG)_LIBS := $(if $(FREETZ_LIB_liblber),liblber.so.$($(PKG)_LIB_VERSION)) $(if $(FREETZ_LIB_libldap),libldap.so.$($(PKG)_LIB_VERSION))
$(PKG)_LIBS_BUILD_DIR := \
	$($(PKG)_DIR)/libraries/liblber/.libs/liblber.so.$($(PKG)_LIB_VERSION) \
	$($(PKG)_DIR)/libraries/libldap/.libs/libldap.so.$($(PKG)_LIB_VERSION)
$(PKG)_LIBS_STAGING_DIR := $(addprefix $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/,$($(PKG)_LIBS))
$(PKG)_LIBS_TARGET_DIR := $(addprefix $($(PKG)_TARGET_LIBDIR)/,$($(PKG)_LIBS))

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_liblber
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libldap

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)
$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --enable-backends=no
$(PKG)_CONFIGURE_OPTIONS += --enable-overlays=no
$(PKG)_CONFIGURE_OPTIONS += --enable-slapd=no
$(PKG)_CONFIGURE_OPTIONS += --with-cyrus-sasl=no
$(PKG)_CONFIGURE_OPTIONS += --with-tls=no


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIBS_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(OPENLDAP_DIR)/libraries/liblber
	$(SUBMAKE) -C $(OPENLDAP_DIR)/libraries/libldap

$($(PKG)_LIBS_STAGING_DIR): $($(PKG)_LIBS_BUILD_DIR)
	$(SUBMAKE) -C $(OPENLDAP_DIR)/libraries/liblber \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-local
	$(SUBMAKE) -C $(OPENLDAP_DIR)/libraries/libldap \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-local
	$(SUBMAKE) -C $(OPENLDAP_DIR)/include \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-local
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib{lber,ldap}.la
	$(RM) -f \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/etc/ldap.conf \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/etc/ldap.conf.default
	@touch -c $@

$($(PKG)_LIBS_TARGET_DIR): $($(PKG)_TARGET_LIBDIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_LIBS_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_LIBS_TARGET_DIR)


$(pkg)-clean:
	-$(SUBMAKE) -C $(OPENLDAP_DIR)/libraries/libldap clean
	-$(SUBMAKE) -C $(OPENLDAP_DIR)/libraries/liblber clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libldap* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblber* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/{lber.h,lber_types.h,ldap.h,ldap_cdefs.h,ldap_schema.h,ldap_utf8.h,slapi-plugin.h,ldap_features.h,ldif.h,openldap.h} \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/etc/ldap*.conf*

$(pkg)-uninstall:
	$(RM) $(OPENLDAP_TARGET_LIBDIR)/libldap*.so* $(OPENLDAP_TARGET_LIBDIR)/liblber*.so*

$(call PKG_ADD_LIB,liblber)
$(call PKG_ADD_LIB,libldap)
$(PKG_FINISH)