$(call PKG_INIT_LIB, 0.15.0)
$(PKG)_LIB_VERSION:=0.15.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=5d84dec684c27b97b921d2f3b73218cb773cf4ea915caee317ac8fc73cef8136
$(PKG)_SITE:=https://github.com/libusb/hidapi/archive/refs/tags
### WEBSITE:=https://libusb.info/hidapi/
### MANPAGE:=https://github.com/libusb/hidapi
### CHANGES:=https://github.com/libusb/hidapi/releases
### CVSREPO:=https://github.com/libusb/hidapi

$(PKG)_BINARY:=$($(PKG)_DIR)/libhidapi-hidraw.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libhidapi-hidraw.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libhidapi-hidraw.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host

# Copy stub libudev files after patches but before configure
$(PKG)_PATCH_POST_CMDS += cp $(CURDIR)/make/libs/hidapi/files/libudev.h linux/libudev.h && cp $(CURDIR)/make/libs/hidapi/files/libudev.c linux/libudev.c

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_FLAGS:STRING="-include stdarg.h -D_GNU_SOURCE $(TARGET_CFLAGS)"
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_BUILD_HIDRAW=ON
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_BUILD_LIBUSB=OFF
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_WITH_UDEV=OFF
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_INSTALL_HEADERS=ON


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(HIDAPI_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(HIDAPI_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(HIDAPI_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libhidapi-hidraw.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/hidapi.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/hidapi/

$(pkg)-uninstall:
	$(RM) $(HIDAPI_TARGET_DIR)/libhidapi-hidraw.so*

$(PKG_FINISH)
