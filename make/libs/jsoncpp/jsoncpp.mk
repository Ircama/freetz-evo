$(call PKG_INIT_LIB, 1.9.8)
$(PKG)_LIB_VERSION:=1.9.8
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=51828cf3574281d2b79ec2a1c56a9e4c20cc1103711321ea96384cffb8d2d904
$(PKG)_SITE:=https://github.com/open-source-parsers/jsoncpp/archive/refs/tags
### WEBSITE:=https://github.com/open-source-parsers/jsoncpp
### CHANGES:=https://github.com/open-source-parsers/jsoncpp/releases
### CVSREPO:=https://github.com/open-source-parsers/jsoncpp

$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/lib/libjsoncpp.so.$($(PKG)_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libjsoncpp.so.$($(PKG)_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libjsoncpp.so.$($(PKG)_VERSION)

# jsoncpp soversion is 27 (used as SONAME), actual file has project version 1.9.8
JSONCPP_LIB_VERSION:=27

$(PKG)_DEPENDS_ON += cmake-host

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_LIBDIR=lib
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_CROSSCOMPILING=ON
$(PKG)_CONFIGURE_OPTIONS += -DJSONCPP_WITH_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DJSONCPP_WITH_EXAMPLE=OFF
$(PKG)_CONFIGURE_OPTIONS += -DJSONCPP_WITH_PKGCONFIG_SUPPORT=ON
$(PKG)_CONFIGURE_OPTIONS += -DJSONCPP_WITH_CMAKE_PACKAGE=ON
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_STATIC_LIBS=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# jsoncpp requires out-of-source builds
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	mkdir -p $(JSONCPP_DIR)/builddir
	cd $(JSONCPP_DIR)/builddir && \
		$(TARGET_CONFIGURE_ENV) $(MAKE_ENV) $(CMAKE) \
		$(JSONCPP_CONFIGURE_OPTIONS) \
		..
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(JSONCPP_DIR)/builddir

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(JSONCPP_DIR)/builddir \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(JSONCPP_DIR)/builddir clean 2>/dev/null || true

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libjsoncpp.so*

$(PKG_FINISH)
