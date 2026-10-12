# telldus -- telldusd, the Tellstick daemon of telldus-core.
#
# The sources are the same archive as the libtelldus-core package in
# make/libs/telldus-core, which also documents the shared source layout; only
# the service/ and tdtool/ subprojects are built here. telldusd owns the USB
# stick through libftdi (the tree's libftdi 0.20 matches the 0.x API this
# source uses) and reads its configuration with libconfuse. tdtool is the
# command line client of the daemon and is shipped with the package, because it
# is the only client available without Domoticz.
#
# Notes:
#  - The release sources refuse to configure without FORCE_COMPILE_FROM_TRUNK,
#    and they ask for cmake_minimum_required(2.6.0), which CMake 4 rejects:
#    CMAKE_POLICY_VERSION_MINIMUM is the override CMake itself documents.
#  - service/CMakeLists.txt uses PKG_SEARCH_MODULE(), a macro that no longer
#    exists in current CMake. It is replaced by FIND_PATH, and the FTDI and
#    confuse paths are passed in explicitly so that the host is never searched.
#  - Upstream hardcodes /etc/tellstick.conf (read only in the image) and
#    /var/state/telldus-core.conf (/var/state does not exist on the box). Both
#    are moved into /mod/etc/conf, the writable directory the freetz
#    configuration framework saves to flash: that is where the daemon stores
#    learned devices and where the web interface writes the configuration.
$(call PKG_INIT_BIN, 2.1.1)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Home Automation

# The archive is the one of the libtelldus-core package (same tag, same URL),
# but the local file name has to differ: the framework generates one download
# rule per package and a second rule for the same file is reported as an
# overriding recipe on every make invocation. dl/ is not version controlled, so
# the cache simply holds the archive twice.
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=203c5a3e05a3bf52e818b98d8385c1ed28237245c9a0920c78213d15093f07e8
$(PKG)_SITE:=https://github.com/telldus/telldus/archive/refs/tags
### WEBSITE:=https://telldus.com/
### CHANGES:=https://github.com/telldus/telldus/releases
### CVSREPO:=https://github.com/telldus/telldus

# The archive root is telldus-2.1.1/ and holds the GUI, the bindings and the
# scheduler as well; the CMake project is the telldus-core/ subdirectory.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/service/telldusd
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/sbin/telldusd
$(PKG)_CTL_BINARY:=$($(PKG)_DIR)/builddir/tdtool/tdtool
$(PKG)_CTL_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/tdtool

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libconfuse
$(PKG)_DEPENDS_ON += libftdi

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_TELLDUS
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libconfuse
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libftdi

# service/CMakeLists.txt uses PKG_SEARCH_MODULE(), a macro that no longer exists
# in current CMake: it is replaced by FIND_PATH, and the include directory is
# passed in explicitly anyway.
#
# The sources call close(), read(), write() and unlink() without including
# <unistd.h>; older libstdc++ pulled it in indirectly, GCC 13 does not. They
# are stored with CRLF line endings, so a patch file would not match - sed does
# not care about the line terminators.
#
# Upstream's two configuration paths do not work here: /etc/tellstick.conf is
# read only in the image and /var/state does not exist. Both are moved into
# /mod/etc/conf, the writable directory the freetz configuration framework
# saves to flash, which is where the daemon stores learned devices and where
# the web interface writes the configuration.
#
# The '#' characters are escaped because they would otherwise start a make
# comment, and the note about the semicolons: the framework joins successive
# additions with a single space, so all commands are kept in one assignment.
# tdtool links the client library through its build path
# (${CMAKE_BINARY_DIR}/client/libtelldus-core.so), which CMake turns into a file
# dependency without a rule of its own: a serial build gets away with it, a
# parallel one fails with "No rule to make target 'client/libtelldus-core.so'".
# The whole line is replaced by the name of the CMake target, which fixes the
# dependency; the pattern avoids a trailing '$' anchor on purpose, because a
# single '$' in a make variable would be swallowed by make.
$(PKG)_PATCH_POST_CMDS += $(SED) -i -e 's|^.*client/libtelldus-core\.so.*|telldus-core|' telldus-core/tdtool/CMakeLists.txt; \
	$(SED) -i -e 's/PKG_SEARCH_MODULE(FTDI libftdi)/FIND_PATH(FTDI_INCLUDEDIR NAMES ftdi.h)/' telldus-core/service/CMakeLists.txt; \
	$(SED) -i -e 's|/etc/tellstick.conf|/mod/etc/conf/tellstick.conf|' telldus-core/service/SettingsConfuse.cpp; \
	$(SED) -i -e 's|/var/state/telldus-core.conf|/mod/etc/conf/tellstick-state.conf|' telldus-core/service/SettingsConfuse.cpp; \
	$(SED) -i -e '/\#include <math.h>/a \#include <unistd.h>' telldus-core/common/Socket_unix.cpp; \
	$(SED) -i -e '/\#include <list>/a \#include <unistd.h>' telldus-core/client/Client.cpp; \
	$(SED) -i -e '/\#include <stdlib.h>/a \#include <unistd.h>' telldus-core/client/telldus-core.cpp; \
	$(SED) -i -e '/\#include <stdlib.h>/a \#include <unistd.h>' telldus-core/service/ClientCommunicationHandler.cpp; \
	$(SED) -i -e '/\#include <list>/a \#include <unistd.h>' telldus-core/service/EventUpdateManager.cpp; \
	$(SED) -i -e '/\#include <stdio.h>/a \#include <stdarg.h>' telldus-core/service/Log.h; \
	$(SED) -i -e 's|d->cfg > 0|d->cfg != NULL|g' -e 's|d->var_cfg > 0|d->var_cfg != NULL|g' telldus-core/service/SettingsConfuse.cpp

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_FLAGS:STRING="$(TARGET_CFLAGS)"
# ProtocolX10.cpp initialises a char array from unsigned char constants (L = 169),
# which is an error since C++11. The values are meant to be used bit by bit, so
# the conversion is intentional and the diagnostic is switched off.
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_CXX_FLAGS:STRING="$(TARGET_CFLAGS) -Wno-narrowing"
$(PKG)_CONFIGURE_OPTIONS += -DFORCE_COMPILE_FROM_TRUNK=TRUE
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5
# tdtool is the only client that works without Domoticz; tdadmin needs ncurses.
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TDTOOL=TRUE
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TDADMIN=FALSE
$(PKG)_CONFIGURE_OPTIONS += -DFTDI_ENGINE=libftdi
$(PKG)_CONFIGURE_OPTIONS += -DFTDI_INCLUDEDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_OPTIONS += -DFTDI_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libftdi.so"
$(PKG)_CONFIGURE_OPTIONS += -DCONFUSE_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libconfuse.so"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# Out-of-source build, so that the sources stay untouched.
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	mkdir -p $(TELLDUS_DIR)/builddir
	cd $(TELLDUS_DIR)/builddir && \
		$(TARGET_CONFIGURE_ENV) $(MAKE_ENV) $(CMAKE) \
		$(TELLDUS_CONFIGURE_OPTIONS) \
		../telldus-core
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TELLDUS_DIR)/builddir

$($(PKG)_CTL_BINARY): $($(PKG)_BINARY)
	@test -x $@

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_CTL_TARGET_BINARY): $($(PKG)_CTL_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg): $($(PKG)_BINARY) $($(PKG)_CTL_BINARY)

# Static files (default daemon configuration, config defaults, save hook, init
# script, web page) are staged through an explicit target: the generic
# $($(PKG)_TARGET_DIR)/root rule never refreshes an existing staging directory.
$(PKG)_STAGING_SOURCES := \
	$(TELLDUS_MAKE_DIR)/files/.language \
	$(TELLDUS_MAKE_DIR)/files/root/etc/default.telldus/telldus.cfg \
	$(TELLDUS_MAKE_DIR)/files/root/etc/default.telldus/telldus.save \
	$(TELLDUS_MAKE_DIR)/files/root/etc/init.d/rc.telldus \
	$(TELLDUS_MAKE_DIR)/files/root/etc/tellstick.conf \
	$(TELLDUS_MAKE_DIR)/files/root/usr/lib/cgi-bin/telldus.cgi
$(PKG)_STAGING_TARGET := $($(PKG)_DEST_DIR)/etc/init.d/rc.telldus

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(TELLDUS_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(TELLDUS_MAKE_DIR)/files,$(TELLDUS_TARGET_DIR))
	chmod 755 \
		$(TELLDUS_DEST_DIR)/etc/init.d/rc.telldus \
		$(TELLDUS_DEST_DIR)/etc/default.telldus/telldus.save \
		$(TELLDUS_DEST_DIR)/usr/lib/cgi-bin/telldus.cgi

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_CTL_TARGET_BINARY) $($(PKG)_STAGING_TARGET)

$(pkg)-clean:
	$(RM) -r $(TELLDUS_BUILD_DIR) $(TELLDUS_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY) $($(PKG)_CTL_TARGET_BINARY)

$(PKG_FINISH)
