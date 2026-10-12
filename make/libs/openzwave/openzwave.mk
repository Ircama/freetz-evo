# Domoticz 2026.4 compiles hardware/OpenZWave.cpp with
# "#include <ValueIDIndexesDefines.h>", and that header only exists in the
# master branch: the v1.6 tag is older than the ValueIDIndexes rework (the
# upstream of the Z-Wave command classes renamed their indexes). The commit is
# therefore pinned instead of the release tag, so that the library matches what
# the hub expects.
$(call PKG_INIT_LIB, 1.6)
$(PKG)_GIT_COMMIT:=3fff11d246a0d558d26110e1db6bd634a1b347c0
# The local file name carries the commit on purpose: an existing download is
# not verified again, so a tree that still has the archive of the release would
# silently build the old sources out of $(DL_DIR).
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION)-$($(PKG)_GIT_COMMIT).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_GIT_COMMIT).tar.gz
$(PKG)_HASH:=37fda7dabc331122c6e53b129ccf0d36720e0f7586049cb34304735c3fdba252
$(PKG)_SITE:=https://github.com/OpenZWave/open-zwave/archive
### WEBSITE:=https://github.com/OpenZWave/open-zwave
### CHANGES:=https://github.com/OpenZWave/open-zwave/releases
### CVSREPO:=https://github.com/OpenZWave/open-zwave

# The GitHub archive unpacks to open-zwave-<commit>/, while freetz expects the
# sources directly in $(PKG)_DIR (openzwave-1.6).
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

$(PKG)_LIB_VERSION:=1.6
$(PKG)_BINARY:=$($(PKG)_DIR)/cpp/build/libopenzwave.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libopenzwave.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libopenzwave.so.$($(PKG)_LIB_VERSION)

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libopenzwave

# Upstream compiles with -Werror, which is not useful for a cross build: the
# sources are not warning-free with GCC 13 (as with the v1.6 tag before the
# update to master).
#
# Utils.cpp picks std::to_string() for C++11 by testing "#if __cplusplus ==
# 201103L": with GCC 13 that equality test never matches and the fallback,
# the static_cast<ostringstream&> trick of 2011, does not compile any more.
# The comparison is turned into a range test instead. Both changes are made
# with $(SED) right after the patches are applied, because the Makefile aligns
# its flags with spaces, which makes a hand-written patch of that line fragile.
$(PKG)_PATCH_POST_CMDS += $(SED) -i -e 's/ -Werror//g' cpp/build/Makefile; \
	$(SED) -i -e 's/__cplusplus==201103L/__cplusplus>=201103L/' cpp/src/Utils.cpp

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# USE_HID=0 keeps the bundled hidapi back end out of the build: its Linux
# implementation is the only reason upstream links -ludev, and libudev is not
# part of this tree. Z-Wave sticks work without it, they are plain serial
# devices.
#
# Upstream ships a plain hand-written Makefile (no configure script), so the
# cross compiler has to be passed as make variables - TARGET_CONFIGURE_ENV can
# not be used as a prefix here, because it would end up in front of the shell
# function that $(SUBMAKE) expands to. The target flags go into CPPFLAGS
# because the Makefile appends to CFLAGS itself (command line variables cannot
# be appended to), and LD has to be set too because support.mk assigns it
# independently of CXX (LD := $(CROSS_COMPILE)g++ would be the host g++).
# AR carries the archive option: the "rc" in ar_option is only defined for
# bitbake builds, upstream expects $(AR) to hold "ar rc" otherwise.
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(OPENZWAVE_DIR)/cpp/build \
		CC=$(TARGET_CC) \
		CXX=$(TARGET_CXX) \
		LD=$(TARGET_CXX) \
		CPPFLAGS="$(TARGET_CFLAGS)" \
		AR="$(TARGET_AR) rc" \
		RANLIB=$(TARGET_RANLIB) \
		PREFIX=/usr USE_HID=0

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(OPENZWAVE_DIR)/cpp/build \
		CC=$(TARGET_CC) \
		CXX=$(TARGET_CXX) \
		LD=$(TARGET_CXX) \
		PREFIX=/usr USE_HID=0 \
		DESTDIR="$(abspath $(TARGET_TOOLCHAIN_STAGING_DIR))" \
		instlibdir=/usr/lib/ \
		pkgconfigdir=/usr/lib/pkgconfig \
		install
	# Domoticz ships its own copy of the OpenZWave device database and the API
	# documentation is not needed on the router, so both are dropped here.
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/etc/openzwave
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/doc/openzwave-*
	# The generated .pc carries the build prefix (and even the build host's
	# lib64, picked up from uname -m), so its paths are rewritten to point into
	# the staging tree, the same way the other libraries in this tree do.
	$(SED) -i \
		-e 's|^prefix=.*|prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr|' \
		-e 's|^exec_prefix=.*|exec_prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr|' \
		-e 's|^libdir=.*|libdir=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib|' \
		-e 's|^includedir=.*|includedir=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/openzwave|' \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libopenzwave.pc

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(OPENZWAVE_DIR)/cpp/build clean
	$(RM) $(OPENZWAVE_DIR)/.configured
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libopenzwave.* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libopenzwave.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/ozw_config
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/openzwave

$(pkg)-uninstall:
	$(RM) $(OPENZWAVE_TARGET_DIR)/libopenzwave.so*

$(PKG_FINISH)
