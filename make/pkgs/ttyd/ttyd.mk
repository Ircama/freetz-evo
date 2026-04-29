$(call PKG_INIT_BIN, 1.7.7)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=039dd995229377caee919898b7bd54484accec3bba49c118e2d5cd6ec51e3650
$(PKG)_SITE:=https://github.com/tsl0922/ttyd/archive/refs/tags
### VERSION:=1.7.7
### WEBSITE:=https://github.com/tsl0922/ttyd
### MANPAGE:=https://github.com/tsl0922/ttyd/blob/main/man/ttyd.1
### CHANGES:=https://github.com/tsl0922/ttyd/releases
### CVSREPO:=https://github.com/tsl0922/ttyd
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/ttyd
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/ttyd

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libuv
$(PKG)_DEPENDS_ON += libwebsockets
$(PKG)_DEPENDS_ON += json-c
$(PKG)_DEPENDS_ON += zlib

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libwebsockets_WITH_SSL

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release

# libuv discovery
$(PKG)_CONFIGURE_OPTIONS += -DLIBUV_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_OPTIONS += -DLIBUV_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libuv.so"

# json-c discovery (json.h installs to usr/include/json-c/json.h)
$(PKG)_CONFIGURE_OPTIONS += -DJSON-C_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/json-c"
$(PKG)_CONFIGURE_OPTIONS += -DJSON-C_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libjson-c.so"

# zlib discovery
$(PKG)_CONFIGURE_OPTIONS += -DZLIB_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_OPTIONS += -DZLIB_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libz.so"

# libwebsockets discovery via cmake package config
$(PKG)_CONFIGURE_OPTIONS += -DLibwebsockets_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/cmake/libwebsockets"

# OpenSSL (only if libwebsockets was built with SSL)
ifeq ($(strip $(FREETZ_LIB_libwebsockets_WITH_SSL)),y)
$(PKG)_DEPENDS_ON += openssl
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_SSL_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libssl.so"
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_CRYPTO_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcrypto.so"
endif


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TTYD_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(TTYD_DIR) clean
	$(RM) $(TTYD_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(TTYD_TARGET_BINARY)

$(PKG_FINISH)
