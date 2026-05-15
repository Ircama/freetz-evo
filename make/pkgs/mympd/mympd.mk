$(call PKG_INIT_BIN, 25.0.2)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=5e482074eb36a7fc6047ecd5bc1cfa707850a4ae936c36bbf0faebd6ed00cfef
$(PKG)_SITE:=https://github.com/jcorporation/myMPD/archive/refs/tags
### WEBSITE:=https://github.com/jcorporation/myMPD
### MANPAGE:=https://github.com/jcorporation/myMPD#readme
### CHANGES:=https://github.com/jcorporation/myMPD/releases
### CVSREPO:=https://github.com/jcorporation/myMPD
### STEWARD:=Ircama
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/mympd/

$(PKG)_CATEGORY:=Audio

$(PKG)_BUILD_DIR:=$($(PKG)_DIR)/builddir
$(PKG)_BINARY:=$($(PKG)_BUILD_DIR)/bin/mympd
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/mympd

$(PKG)_DEPENDS_ON += cmake-host openssl pcre2

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX=/usr
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_BUILD_TESTING=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_DOC=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_DOC_HTML=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_MANPAGES=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_STARTUP_SCRIPT=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_EMBEDDED_ASSETS=ON
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_EMBEDDED_LIBMPDCLIENT=ON
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_ENABLE_EXPERIMENTAL=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_ENABLE_FLAC=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_ENABLE_IPV6=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_ENABLE_LIBID3TAG=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_ENABLE_LUA=OFF
$(PKG)_CONFIGURE_OPTIONS += -DMYMPD_ENABLE_UTF8=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_INCLUDE_DIR=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_SSL_LIBRARY=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libssl.so
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_CRYPTO_LIBRARY=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcrypto.so
$(PKG)_CONFIGURE_OPTIONS += -DPCRE2_INCLUDE_DIR=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include
$(PKG)_CONFIGURE_OPTIONS += -DPCRE2_LIBRARY=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libpcre2-8.so

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.build-prereq-checked $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	$(CONFCMAKE_NO_BUILD_SYSTEM_ARGUMENTS) \
		cd $(MYMPD_DIR); \
		rm -rf builddir; \
		mkdir -p builddir; \
		cd builddir; \
		cmake .. \
		$(MYMPD_CONFIGURE_OPTIONS)
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(MYMPD_BUILD_DIR) -j1

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(MYMPD_BUILD_DIR) DESTDIR="$(MYMPD_DEST_DIR)" install
	$(RM) -f $(MYMPD_DEST_DIR)/usr/bin/mympd-config
	$(TARGET_STRIP) $(MYMPD_TARGET_BINARY) 2>/dev/null || true

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(MYMPD_BUILD_DIR) clean
	$(RM) -r $(MYMPD_BUILD_DIR) $(MYMPD_DIR)/.configured

$(pkg)-uninstall:
	$(RM) -f \
		$(MYMPD_DEST_DIR)/usr/bin/mympd \
		$(MYMPD_DEST_DIR)/usr/bin/mympd-config

$(PKG_FINISH)
