$(call PKG_INIT_BIN, 7.2)
# Patch 001-fix-gpt-sys-types-static-init.patch (src/partgpt.c): testdisk's
# gpt_sys_types[] static array is initialized with the GPT_ENT_TYPE_* macros,
# which are compound literals with a `(const efi_guid_t)` cast. The old
# GCC 4.6.4 toolchain rejects such casts in static initializers ("initializer
# element is not constant"). The patch expands the array entries to plain
# brace initializers (no cast) inside the array only; the macros themselves
# keep the cast because they are also used as expressions (guid_cmp).
# This is a GCC 4.6 quirk, not uClibc-specific -> source patch (no gate, no
# regression on any toolchain).
$(PKG)_CATEGORY_PKGS:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f3fe7ec02cafcbe792a4c783976de3a6312963b0ce8a613d38adbcd8bdca0517
$(PKG)_SITE:=https://github.com/cgsecurity/testdisk/archive/refs/tags
### WEBSITE:=https://www.cgsecurity.org/wiki/TestDisk
### CHANGES:=https://github.com/cgsecurity/testdisk/releases
### CVSREPO:=https://github.com/cgsecurity/testdisk
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARIES_ALL := testdisk photorec fidentify
$(PKG)_BINARIES := $(call PKG_SELECTED_SUBOPTIONS,$($(PKG)_BINARIES_ALL))
$(PKG)_BINARIES_FOR_BUILD := $(if $(strip $($(PKG)_BINARIES)),$($(PKG)_BINARIES),$($(PKG)_BINARIES_ALL))
$(PKG)_BINARIES_BUILD_DIR := $($(PKG)_BINARIES_FOR_BUILD:%=$($(PKG)_DIR)/src/%)
$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/sbin/%)
$(PKG)_EXCLUDED += $(patsubst %,$($(PKG)_DEST_DIR)/usr/sbin/%,$(filter-out $($(PKG)_BINARIES),$($(PKG)_BINARIES_ALL)))

# TUI requires ncursesw; always link it since testdisk's configure script
# requires at least one ncurses variant to be present.
$(PKG)_DEPENDS_ON += ncursesw

# testdisk 7.2 configure.ac has a broken UUID library check
# (AC_CHECK_LIB argument order is inverted). Disable UUID to avoid
# configure failures in the cross-compilation environment.
$(PKG)_CONFIGURE_OPTIONS += --without-uuid
$(PKG)_CONFIGURE_OPTIONS += --enable-missing-uuid-ok
# testdisk's configure enables -fstack-protector-strong by default, which links
# -lssp/-lssp_nonshared; uClibc (all versions) does not provide libssp, so the
# link fails with "cannot find -lssp". Disable stack protection (not uClibc-gated;
# works fine on every toolchain, no regression).
$(PKG)_CONFIGURE_OPTIONS += --disable-stack-protector

# Disable optional dependencies that are not available or needed in
# the embedded freetz environment.
$(PKG)_CONFIGURE_OPTIONS += --without-ext2fs
$(PKG)_CONFIGURE_OPTIONS += --without-ntfs
$(PKG)_CONFIGURE_OPTIONS += --without-ntfs3g
$(PKG)_CONFIGURE_OPTIONS += --without-jpeg
$(PKG)_CONFIGURE_OPTIONS += --without-ewf
$(PKG)_CONFIGURE_OPTIONS += --without-reiserfs
$(PKG)_CONFIGURE_OPTIONS += --without-iconv
$(PKG)_CONFIGURE_OPTIONS += --disable-qt

# GitHub tarballs for testdisk do not include a pre-generated configure
# script; regenerate it with autoreconf before the standard configure step.
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TESTDISK_DIR) all

$($(PKG)_BINARIES_TARGET_DIR): $($(PKG)_DEST_DIR)/usr/sbin/%: $($(PKG)_DIR)/src/%
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_BUILD_DIR) $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	@if [ -f "$(TESTDISK_DIR)/Makefile" ]; then \
		$(SUBMAKE) -C $(TESTDISK_DIR) clean; \
	fi

$(pkg)-uninstall:
	$(RM) $(TESTDISK_BINARIES_ALL:%=$(TESTDISK_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
