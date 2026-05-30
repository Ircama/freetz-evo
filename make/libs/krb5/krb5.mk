$(call PKG_INIT_LIB, 1.21.3)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b7a4cd5ead67fb08b980b21abd150ff7217e85ea320c9ed0c6dadd304840ad35
$(PKG)_SITE:=https://web.mit.edu/kerberos/dist/krb5/1.21
### WEBSITE:=https://web.mit.edu/kerberos/
### CHANGES:=https://web.mit.edu/kerberos/dist/
### CVSREPO:=https://github.com/krb5/krb5

$(PKG)_BASE_LIBS := libcom_err.so.3.0 libk5crypto.so.3.1 libkrb5support.so.0.1
$(PKG)_MAIN_LIBS := $(if $(FREETZ_LIB_libkrb5),libkrb5.so.3.3)
$(PKG)_GSS_LIBS := $(if $(FREETZ_LIB_libgssapi_krb5),libgssapi_krb5.so.2.2)
$(PKG)_LIBS := $(if $(FREETZ_LIB_libkrb5),$($(PKG)_BASE_LIBS) $($(PKG)_MAIN_LIBS)) $($(PKG)_GSS_LIBS)

$(PKG)_BINARY := $($(PKG)_DIR)/src/lib/krb5/.libs/libkrb5.so.3.3
$(PKG)_STAGING_BINARIES := $($(PKG)_LIBS:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%)
$(PKG)_TARGET_BINARIES := $($(PKG)_LIBS:%=$($(PKG)_TARGET_DIR)/%)

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libkrb5
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libgssapi_krb5

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	(cd $(KRB5_DIR)/src; \
		$(RM) -r config.cache; \
		$(TARGET_CONFIGURE_ENV) \
		cross_compiling=yes \
		krb5_cv_attr_constructor_destructor=yes,yes \
		krb5_cv_sys_rcdir=/tmp \
		ac_cv_func_regcomp=yes \
		ac_cv_printf_positional=yes \
		ac_cv_file__etc_environment=no \
		ac_cv_file__etc_TIMEZONE=no \
		ac_cv_header_keyutils_h=no \
		./configure \
			--build=$(GNU_HOST_NAME) \
			--host=$(GNU_TARGET_NAME) \
			--target=$(GNU_TARGET_NAME) \
			--prefix=/usr \
			--disable-rpath \
			--enable-shared \
			--disable-static \
			--without-tcl \
			--without-tls-impl \
			--without-system-verto \
			--without-libedit \
			--without-readline \
			--without-system-et \
			--without-system-ss \
			--disable-pkinit \
			--with-size-optimizations \
	)
	touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(KRB5_DIR)/src

$($(PKG)_STAGING_BINARIES): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(KRB5_DIR)/src DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" install
	$(SED) -i \
		-e 's|^prefix=.*|prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr|' \
		-e 's|^exec_prefix=.*|exec_prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr|' \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/krb5-config
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/sbin \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/man
	@touch -c $@

$($(PKG)_TARGET_BINARIES): $($(PKG)_TARGET_DIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARIES)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARIES)

$(pkg)-clean:
	-$(SUBMAKE) -C $(KRB5_DIR)/src clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/{krb5.h,gssapi,profile.h,com_err.h,krb5} \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib{com_err,gssapi_krb5,k5crypto,krb5,krb5support}* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/{krb5,krb5-gssapi}.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/krb5-config

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/lib{com_err,gssapi_krb5,k5crypto,krb5,krb5support}*.so*

$(PKG_FINISH)
