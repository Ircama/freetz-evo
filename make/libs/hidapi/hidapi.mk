$(call PKG_INIT_LIB, 0.15.0)
# Patch 002-fix-bus-spi-fallback.patch (linux/hid.c): the hidraw backend uses
# BUS_SPI, which was added to <linux/input.h> only in kernel 4.10. AVM devices
# use older kernel headers (2.6.32/3.10/4.4/4.9, including with uClibc 1.0.58
# on MIPS), so BUS_SPI is undefined there and linux/hid.c fails with
# "'BUS_SPI' undeclared". The patch defines a fallback (#define BUS_SPI 0x1A).
# This is a kernel-headers issue, NOT uClibc-specific -> source patch instead
# of a uClibc gate (no regression on any toolchain).
#
# Patch 003-fix-libusb-pthread-barrier.patch (libusb/hidapi_thread_pthread.h):
# the libusb backend uses pthread_barrier_* for the 2-party read-thread
# startup handshake. Old uClibc (0.9.x, e.g. 0.9.32.1 on 3270v3) *declares*
# pthread_barrier_* in <pthread.h> but does NOT implement them in libpthread,
# so libhidapi-libusb.so ends up with undefined references and consumers like
# avrdude fail to link. The patch replaces the barrier with an equivalent
# mutex+cond handshake (only pthread_mutex/pthread_cond are used, available on
# every libc), so it is applied unconditionally and causes no regression on
# modern toolchains (uClibc-ng 1.0.58+, glibc, musl).
$(PKG)_LIB_VERSION:=0.15.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=5d84dec684c27b97b921d2f3b73218cb773cf4ea915caee317ac8fc73cef8136
$(PKG)_SITE:=https://github.com/libusb/hidapi/archive/refs/tags
### WEBSITE:=https://libusb.info/hidapi/
### MANPAGE:=https://github.com/libusb/hidapi
### CHANGES:=https://github.com/libusb/hidapi/releases
### CVSREPO:=https://github.com/libusb/hidapi

# libusb backend (always built) — uses usbfs directly, no kernel HID/INPUT needed.
# hidraw backend (optional, FREETZ_LIB_hidapi_hidraw) — requires kernel HID support.
# Uses out-of-source build (builddir/) to avoid cmake timestamp churn.
$(PKG)_BUILD_SUBDIR:=builddir
$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/src/libusb/libhidapi-libusb.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libhidapi-libusb.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libhidapi-libusb.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libusb1

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_hidapi
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libusb1
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_hidapi_hidraw

# Copy stub libudev files after patches but before configure
$(PKG)_PATCH_POST_CMDS += \
  [ -f linux/libudev.h ] || cp $(CURDIR)/make/libs/hidapi/files/libudev.h linux/libudev.h; \
  [ -f linux/libudev.c ] || cp $(CURDIR)/make/libs/hidapi/files/libudev.c linux/libudev.c

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_FLAGS:STRING="-include stdarg.h -D_GNU_SOURCE $(TARGET_CFLAGS)"
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_BUILD_HIDRAW=$(if $(FREETZ_LIB_hidapi_hidraw),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_BUILD_LIBUSB=ON
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_WITH_UDEV=OFF
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DHIDAPI_INSTALL_HEADERS=ON

# --- hidraw backend variables (only if enabled) ---
ifeq ($(strip $(FREETZ_LIB_hidapi_hidraw)),y)
$(PKG)_BINARY_HIDRAW:=$($(PKG)_DIR)/builddir/src/hidraw/libhidapi-hidraw.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY_HIDRAW:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libhidapi-hidraw.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY_HIDRAW:=$($(PKG)_TARGET_DIR)/libhidapi-hidraw.so.$($(PKG)_LIB_VERSION)
endif


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

# --- hidraw backend rules (only if enabled) ---
ifeq ($(strip $(FREETZ_LIB_hidapi_hidraw)),y)

$($(PKG)_STAGING_BINARY_HIDRAW): $($(PKG)_STAGING_BINARY)
	@touch $@

$($(PKG)_TARGET_BINARY_HIDRAW): $($(PKG)_STAGING_BINARY_HIDRAW)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY_HIDRAW)
$(pkg)-precompiled: $($(PKG)_TARGET_BINARY_HIDRAW)

endif


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
