$(call PKG_INIT_LIB, 0.15.0)
$(PKG)_LIB_VERSION:=0.15.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=5d84dec684c27b97b921d2f3b73218cb773cf4ea915caee317ac8fc73cef8136
$(PKG)_SITE:=https://github.com/libusb/hidapi/archive/refs/tags
### WEBSITE:=https://libusb.info/hidapi/
### MANPAGE:=https://github.com/libusb/hidapi
### CHANGES:=https://github.com/libusb/hidapi/releases
### CVSREPO:=https://github.com/libusb/hidapi

# libusb backend (does not require kernel HID/INPUT subsystem)
# Uses out-of-source build (builddir/) to avoid cmake timestamp churn.
$(PKG)_BUILD_SUBDIR:=builddir
$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/src/libusb/libhidapi-libusb.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libhidapi-libusb.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libhidapi-libusb.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libusb1

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_hidapi
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libusb1

# Copy stub libudev files after patches but before configure
$(PKG)_PATCH_POST_CMDS += \
  [ -f linux/libudev.h ] || cp $(CURDIR)/make/libs/hidapi/files/libudev.h linux/libudev.h; \
  [ -f linux/libudev.c ] || cp $(CURDIR)/make/libs/hidapi/files/libudev.c linux/libudev.c

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_FLAGS:STRING="-include stdarg.h -D_GNU_SOURCE $(TARGET_CFLAGS)"
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_BUILD_HIDRAW=OFF
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_BUILD_LIBUSB=ON
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_WITH_UDEV=OFF
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_INSTALL_HEADERS=ON


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# Out-of-source cmake build (avoids in-source timestamp churn)
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	mkdir -p $(HIDAPI_DIR)/builddir
	cd $(HIDAPI_DIR)/builddir && \
		$(TARGET_CONFIGURE_ENV) $(MAKE_ENV) $(CMAKE) \
		$(HIDAPI_CONFIGURE_OPTIONS) \
		..
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(HIDAPI_DIR)/builddir

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(HIDAPI_DIR)/builddir \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(HIDAPI_DIR)/builddir clean 2>/dev/null || true
	$(RM) -r \
		$(HIDAPI_DIR)/builddir \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libhidapi-*.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/hidapi.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/hidapi/

$(pkg)-uninstall:
	$(RM) $(HIDAPI_TARGET_DIR)/libhidapi-*.so*

$(PKG_FINISH)
