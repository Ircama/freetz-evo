# telldus-core 2.1.1 - client library of the Tellstick driver.
#
# Notes:
#  - The GitHub tag archive root is telldus-2.1.1/ and it also contains the
#    GUI, the bindings, the scheduler and the daemon; TARBALL_STRIP_COMPONENTS
#    drops that first directory, and the CMake project used here is the
#    telldus-core/ subdirectory.
#  - Only libtelldus-core is built. Upstream has a switch for the tdtool and
#    tdadmin helpers (tdadmin needs ncurses), but none for the service, so
#    service/ is taken out of the build with a sed in PATCH_POST_CMDS: telldusd
#    links libftdi and libconfuse and it is a separate concern from this
#    library.
#  - Upstream refuses to configure release sources unless
#    FORCE_COMPILE_FROM_TRUNK is set.
$(call PKG_INIT_LIB, 2.1.1)
$(PKG)_LIB_VERSION:=2.1.1
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=203c5a3e05a3bf52e818b98d8385c1ed28237245c9a0920c78213d15093f07e8
$(PKG)_SITE:=https://github.com/telldus/telldus/archive/refs/tags
### WEBSITE:=https://telldus.com/
### CHANGES:=https://github.com/telldus/telldus/releases
### CVSREPO:=https://github.com/telldus/telldus

$(PKG)_TARBALL_STRIP_COMPONENTS := 1

$(PKG)_BUILD_SUBDIR:=builddir
$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/client/libtelldus-core.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtelldus-core.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libtelldus-core.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libtelldus_core

# Only libtelldus-core is built: the service subdirectory is removed here
# because upstream has no switch for it, and telldusd links libftdi and
# libconfuse and belongs to a package of its own. The line is deleted rather
# than commented out because a '#' inside a make variable assignment starts a
# comment and would cut off the rest of the command, and the pattern has no
# '$$' anchor because the variable is expanded twice by the framework.
# Note: the framework joins successive additions with a single space, so the
# semicolon separating the commands is part of the assignment.
$(PKG)_PATCH_POST_CMDS += $(SED) -i -e '/ADD_SUBDIRECTORY(service)/d' telldus-core/CMakeLists.txt;

# The sources call close(), read(), write() and unlink() without including
# <unistd.h>: older libstdc++ pulled it in indirectly, GCC 13 does not. They
# are stored with CRLF line endings, so a patch file would not match - sed does
# not care about the line terminators. The '#' characters are escaped because
# they would otherwise start a make comment.
$(PKG)_PATCH_POST_CMDS += $(SED) -i -e '/\#include <math.h>/a \#include <unistd.h>' telldus-core/common/Socket_unix.cpp; \
	$(SED) -i -e '/\#include <list>/a \#include <unistd.h>' telldus-core/client/Client.cpp; \
	$(SED) -i -e '/\#include <stdlib.h>/a \#include <unistd.h>' telldus-core/client/telldus-core.cpp

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_FLAGS:STRING="$(TARGET_CFLAGS)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_CXX_FLAGS:STRING="$(TARGET_CFLAGS)"
# Upstream guards the whole project with this switch and errors out without it.
$(PKG)_CONFIGURE_OPTIONS += -DFORCE_COMPILE_FROM_TRUNK=TRUE
# telldus-core still asks for cmake_minimum_required(VERSION 2.6.0), and CMake
# 4 refuses to configure anything below 3.5. This is the override CMake itself
# documents; older releases simply ignore the setting.
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5
# tdtool is not shipped and tdadmin needs ncurses.
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TDTOOL=FALSE
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TDADMIN=FALSE

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# Out-of-source build, so that the sources stay untouched.
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	mkdir -p $(TELLDUS_CORE_DIR)/builddir
	cd $(TELLDUS_CORE_DIR)/builddir && \
		$(TARGET_CONFIGURE_ENV) $(MAKE_ENV) $(CMAKE) \
		$(TELLDUS_CORE_CONFIGURE_OPTIONS) \
		../telldus-core
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TELLDUS_CORE_DIR)/builddir

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(TELLDUS_CORE_DIR)/builddir \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(TELLDUS_CORE_DIR)/builddir clean 2>/dev/null || true
	$(RM) -r \
		$(TELLDUS_CORE_DIR)/builddir \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtelldus-core.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/telldus-core.h

$(pkg)-uninstall:
	$(RM) $(TELLDUS_CORE_TARGET_DIR)/libtelldus-core.so*

$(PKG_FINISH)
