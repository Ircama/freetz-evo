$(call PKG_INIT_LIB, 0.8.1)
$(PKG)_LIB_VERSION:=4.0
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ba8a282ecd92d0033f5656bb20dfc6ea3fb83f90ba69291ac8f7beba42dcffcf
$(PKG)_SITE:=https://github.com/JuliaMath/openlibm/archive/refs/tags
### WEBSITE:=https://openlibm.org/
### CHANGES:=https://github.com/JuliaMath/openlibm/releases
### CVSREPO:=https://github.com/JuliaMath/openlibm

$(PKG)_CATEGORY_LIBS:=Multi precision arithmetic libs
$(PKG)_BINARY:=$($(PKG)_DIR)/libopenlibm.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libopenlibm.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libopenlibm.so.$($(PKG)_LIB_VERSION)


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_BINARY): $($(PKG)_DIR)/.unpacked
	$(SUBMAKE) -C $(OPENLIBM_DIR) \
		CC="$(TARGET_CC)" \
		AR="$(TARGET_AR)" \
		RANLIB="$(TARGET_RANLIB)"

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(OPENLIBM_DIR) \
		CC="$(TARGET_CC)" \
		AR="$(TARGET_AR)" \
		RANLIB="$(TARGET_RANLIB)" \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		prefix="/usr" \
		libdir="/usr/lib" \
		includedir="/usr/include" \
		pkgconfigdir="/usr/lib/pkgconfig" \
		install

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(OPENLIBM_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libopenlibm*.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libopenlibm.a \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/openlibm.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/openlibm/

$(pkg)-uninstall:
	$(RM) $(OPENLIBM_TARGET_DIR)/libopenlibm*.so*

$(PKG_FINISH)
