# Version selection based on Kconfig
$(call PKG_INIT_BIN, $(if $(FREETZ_UTIL_LINUX_VERSION_2_27_1),2.27.1,2.41))
$(PKG)_CATEGORY:=Disk Tools

# Legacy version 2.27.1 (minimal, with patches)
$(PKG)_SOURCE_2.27.1:=util-linux-2.27.1.tar.xz
$(PKG)_HASH_2.27.1:=0a818fcdede99aec43ffe6ca5b5388bff80d162f2f7bd4541dca94fecb87a290
$(PKG)_BINARIES_2.27.1:=blkid
$(PKG)_BINARIES_WITH_SUFFIX_2.27.1:=blkid
$(PKG)_BINARIES_NO_SUFFIX_2.27.1:=

# Modern version 2.41 (full featured, no patches needed)
$(PKG)_SOURCE_2.41:=util-linux-2.41.tar.xz
$(PKG)_HASH_2.41:=81ee93b3cfdfeb7d7c4090cedeba1d7bbce9141fd0b501b686b3fe475ddca4c6

# lsfd requires BPF_OBJ_NAME_LEN from target linux/bpf.h.
# On kernels < 5.8 the constant is missing; the patch
# 200-lsfd-bpf-obj-name-len-fallback.patch adds the fallback define, and
# we override the configure cache variable so autoconf accepts it.
UTIL_LINUX_BPF_HEADER:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/linux/bpf.h
UTIL_LINUX_HAS_BPF_OBJ_NAME_LEN:=$(shell [ -r "$(UTIL_LINUX_BPF_HEADER)" ] && grep -q "BPF_OBJ_NAME_LEN" "$(UTIL_LINUX_BPF_HEADER)" && echo y || echo n)
UTIL_LINUX_ENABLE_LSFD:=$(if $(filter y,$(FREETZ_UTIL_LINUX_LSFD)),y,n)

# Build list of selected utilities for version 2.41
$(PKG)_BINARIES_2.41:=
$(PKG)_BINARIES_WITH_SUFFIX_2.41:=
$(PKG)_BINARIES_NO_SUFFIX_2.41:=

# Macro to add a binary conditionally
# $1 = config name (e.g., BLKID)
# $2 = binary name (e.g., blkid)
# $3 = suffix type: "with" or "no"
define UTIL_LINUX_ADD_BINARY
ifeq ($$(strip $$(FREETZ_UTIL_LINUX_$(1))),y)
$$(PKG)_BINARIES_2.41+=$(2)
ifeq ($(3),with)
$$(PKG)_BINARIES_WITH_SUFFIX_2.41+=$(2)
else
$$(PKG)_BINARIES_NO_SUFFIX_2.41+=$(2)
endif
endif
endef

$(eval $(call UTIL_LINUX_ADD_BINARY,BLKID,blkid,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,FDISK,fdisk,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,SFDISK,sfdisk,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,BLOCKDEV,blockdev,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,PARTX,partx,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,PARTX,addpart,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,PARTX,delpart,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,PARTX,resizepart,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,FINDFS,findfs,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,WIPEFS,wipefs,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,LOSETUP,losetup,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,MKSWAP,mkswap,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,SWAPON,swapon,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,LSBLK,lsblk,no))
ifeq ($(strip $(UTIL_LINUX_ENABLE_LSFD)),y)
$(PKG)_BINARIES_2.41+=lsfd
$(PKG)_BINARIES_NO_SUFFIX_2.41+=lsfd
endif
$(eval $(call UTIL_LINUX_ADD_BINARY,CFDISK,cfdisk,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,FINDMNT,findmnt,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,UNSHARE,unshare,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,UUIDGEN,uuidgen,with))
$(eval $(call UTIL_LINUX_ADD_BINARY,UUIDPARSE,uuidparse,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,LASTLOG2,lastlog2,no))
$(eval $(call UTIL_LINUX_ADD_BINARY,MOUNTPOINT,mountpoint,no))

ifeq ($(strip $(UTIL_LINUX_ENABLE_LSFD)),y)
ifeq ($(strip $(UTIL_LINUX_HAS_BPF_OBJ_NAME_LEN)),n)
# Header lacks BPF_OBJ_NAME_LEN (kernel < 5.8): override the configure check;
# the source fallback is provided by 200-lsfd-bpf-obj-name-len-fallback.patch.
$(PKG)_CONFIGURE_ENV += ac_cv_have_decl_BPF_OBJ_NAME_LEN=yes
endif
endif


# Select version-specific variables
$(PKG)_SOURCE:=$($(PKG)_SOURCE_$($(PKG)_VERSION))
$(PKG)_HASH:=$($(PKG)_HASH_$($(PKG)_VERSION))
$(PKG)_SITE:=@KERNEL/linux/utils/util-linux/v$(call GET_MAJOR_VERSION,$($(PKG)_VERSION))

# Select version-specific patches directory
$(PKG)_CONDITIONAL_PATCHES+=$($(PKG)_VERSION)

### WEBSITE:=https://en.wikipedia.org/wiki/Util-linux
### MANPAGE:=https://linux.die.net/man/8/blkid
### CHANGES:=https://mirrors.kernel.org/pub/linux/utils/util-linux/
### CVSREPO:=https://git.kernel.org/pub/scm/utils/util-linux/util-linux.git

# Binaries configuration per version
$(PKG)_BINARIES:=$($(PKG)_BINARIES_$($(PKG)_VERSION))
$(PKG)_BINARIES_WITH_SUFFIX:=$($(PKG)_BINARIES_WITH_SUFFIX_$($(PKG)_VERSION))
$(PKG)_BINARIES_NO_SUFFIX:=$($(PKG)_BINARIES_NO_SUFFIX_$($(PKG)_VERSION))

# Suffix to add to util-linux binaries that conflict with busybox
$(PKG)_BINARIES_SUFFIX:=-ng

$(PKG)_BINARIES_BUILD_DIR:=$($(PKG)_BINARIES:%=$($(PKG)_DIR)/%)
$(PKG)_BINARIES_WITH_SUFFIX_TARGET_DIR:=$($(PKG)_BINARIES_WITH_SUFFIX:%=$($(PKG)_DEST_DIR)/sbin/%$($(PKG)_BINARIES_SUFFIX))
$(PKG)_BINARIES_NO_SUFFIX_TARGET_DIR:=$($(PKG)_BINARIES_NO_SUFFIX:%=$($(PKG)_DEST_DIR)/sbin/%)
$(PKG)_BLOCKDEV_WITH_SUFFIX_TARGET:=$($(PKG)_DEST_DIR)/sbin/blockdev$($(PKG)_BINARIES_SUFFIX)
$(PKG)_BLOCKDEV_NG_TARGET:=$($(PKG)_DEST_DIR)/sbin/blockdev-ng

# Version-specific configure commands
ifeq ($(strip $(FREETZ_UTIL_LINUX_VERSION_2_27_1)),y)
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
else
$(PKG)_CONFIGURE_PRE_CMDS += GTKDOCIZE=/bin/true $(AUTORECONF)
endif

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_ENV += scanf_cv_alloc_modifier=no

# Build shared libs only when a util-linux shared library is requested.
# Without this selection, keep --enable-shared=no to prevent conflicts
# with e2fsprogs' libblkid.so.1.0 / libuuid.so.1.2 in the staging dir.
ifneq ($(strip $(FREETZ_LIB_libblkid)$(FREETZ_LIB_libmount)$(FREETZ_LIB_libsmartcols)$(FREETZ_LIB_libfdisk)$(FREETZ_LIB_liblastlog2)),)
$(PKG)_CONFIGURE_OPTIONS += --enable-shared
else
# Do not build any shared library to
# 1) prevent conflicts with e2fsprogs' ones
# 2) force them to be linked in statically
$(PKG)_CONFIGURE_OPTIONS += --enable-shared=no
endif

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libblkid FREETZ_LIB_libmount FREETZ_LIB_libsmartcols FREETZ_LIB_libfdisk FREETZ_LIB_liblastlog2
$(PKG)_REBUILD_SUBOPTS += FREETZ_UTIL_LINUX_UNSHARE

$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --without-libiconv-prefix
$(PKG)_CONFIGURE_OPTIONS += --without-libintl-prefix
$(PKG)_CONFIGURE_OPTIONS += --without-audit
$(PKG)_CONFIGURE_OPTIONS += --without-libz
$(PKG)_CONFIGURE_OPTIONS += --without-python
$(PKG)_CONFIGURE_OPTIONS += --without-readline
$(PKG)_CONFIGURE_OPTIONS += --without-selinux
$(PKG)_CONFIGURE_OPTIONS += --without-slang
$(PKG)_CONFIGURE_OPTIONS += --without-smack
$(PKG)_CONFIGURE_OPTIONS += --without-systemd
$(PKG)_CONFIGURE_OPTIONS += --without-termcap
$(PKG)_CONFIGURE_OPTIONS += --without-udev
$(PKG)_CONFIGURE_OPTIONS += --without-user
$(PKG)_CONFIGURE_OPTIONS += --without-utempter
$(PKG)_CONFIGURE_OPTIONS += --without-util
$(PKG)_CONFIGURE_OPTIONS += --disable-bash-completion
$(PKG)_CONFIGURE_OPTIONS += --disable-colors-default
$(PKG)_CONFIGURE_OPTIONS += --disable-tls

$(PKG)_CONFIGURE_OPTIONS += --disable-agetty
$(PKG)_CONFIGURE_OPTIONS += --disable-bfs
$(PKG)_CONFIGURE_OPTIONS += --disable-cal
$(PKG)_CONFIGURE_OPTIONS += --disable-chfn-chsh
$(PKG)_CONFIGURE_OPTIONS += --disable-cramfs
$(PKG)_CONFIGURE_OPTIONS += --disable-eject
$(PKG)_CONFIGURE_OPTIONS += --disable-fallocate
$(PKG)_CONFIGURE_OPTIONS += --disable-fdformat
$(PKG)_CONFIGURE_OPTIONS += --disable-fsck
$(PKG)_CONFIGURE_OPTIONS += --disable-hwclock
$(PKG)_CONFIGURE_OPTIONS += --disable-kill
$(PKG)_CONFIGURE_OPTIONS += --disable-last
$(PKG)_CONFIGURE_OPTIONS += --enable-libmount

# Version-specific options
ifeq ($(strip $(FREETZ_UTIL_LINUX_VERSION_2_27_1)),y)
# Legacy 2.27.1: minimal build
$(PKG)_CONFIGURE_OPTIONS += --disable-libsmartcols
$(PKG)_CONFIGURE_OPTIONS += --disable-losetup
$(PKG)_CONFIGURE_OPTIONS += --disable-libfdisk
$(PKG)_CONFIGURE_OPTIONS += --disable-liblastlog2
else
# Modern 2.41: enable additional features
ifneq ($(strip $(FREETZ_UTIL_LINUX_LSBLK)$(FREETZ_UTIL_LINUX_CFDISK)),)
$(PKG)_DEPENDS_ON += ncursesw
$(PKG)_CONFIGURE_OPTIONS += --with-ncursesw
endif
ifneq ($(strip $(FREETZ_UTIL_LINUX_FDISK)$(FREETZ_UTIL_LINUX_SFDISK)$(FREETZ_UTIL_LINUX_CFDISK)$(FREETZ_LIB_libfdisk)),)
$(PKG)_CONFIGURE_OPTIONS += --enable-fdisks
else
$(PKG)_CONFIGURE_OPTIONS += --disable-fdisks
endif
ifneq ($(strip $(FREETZ_UTIL_LINUX_CFDISK)$(FREETZ_UTIL_LINUX_FDISK)$(FREETZ_UTIL_LINUX_SFDISK)$(FREETZ_LIB_libfdisk)),)
$(PKG)_CONFIGURE_OPTIONS += --enable-libfdisk
else
$(PKG)_CONFIGURE_OPTIONS += --disable-libfdisk
endif
ifeq ($(strip $(FREETZ_UTIL_LINUX_PARTX)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-partx
else
$(PKG)_CONFIGURE_OPTIONS += --disable-partx
endif
ifeq ($(strip $(FREETZ_UTIL_LINUX_LOSETUP)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-losetup
else
$(PKG)_CONFIGURE_OPTIONS += --disable-losetup
endif
ifeq ($(strip $(FREETZ_UTIL_LINUX_LSBLK)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-lsblk
else
$(PKG)_CONFIGURE_OPTIONS += --disable-lsblk
endif
ifeq ($(strip $(UTIL_LINUX_ENABLE_LSFD)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-lsfd
else
$(PKG)_CONFIGURE_OPTIONS += --disable-lsfd
endif

ifneq ($(strip $(FREETZ_UTIL_LINUX_BLKID)$(FREETZ_UTIL_LINUX_FINDFS)$(FREETZ_UTIL_LINUX_WIPEFS)),)
$(PKG)_CONFIGURE_OPTIONS += --enable-blkid
else
$(PKG)_CONFIGURE_OPTIONS += --disable-blkid
endif
ifeq ($(strip $(FREETZ_UTIL_LINUX_WIPEFS)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-wipefs
else
$(PKG)_CONFIGURE_OPTIONS += --disable-wipefs
endif
ifeq ($(strip $(FREETZ_UTIL_LINUX_UUIDGEN)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-uuidgen
else
$(PKG)_CONFIGURE_OPTIONS += --disable-uuidgen
endif
ifeq ($(strip $(FREETZ_UTIL_LINUX_UNSHARE)),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-unshare
else
$(PKG)_CONFIGURE_OPTIONS += --disable-unshare
endif
ifeq ($(strip $(FREETZ_LIB_liblastlog2)),y)
$(PKG)_DEPENDS_ON += sqlite
$(PKG)_CONFIGURE_OPTIONS += --enable-liblastlog2
else
$(PKG)_CONFIGURE_OPTIONS += --disable-liblastlog2
endif
$(PKG)_CONFIGURE_OPTIONS += --disable-gtk-doc
$(PKG)_CONFIGURE_OPTIONS += --disable-year2038
$(PKG)_CONFIGURE_OPTIONS += --enable-libsmartcols
endif

$(PKG)_CONFIGURE_OPTIONS += --disable-line
$(PKG)_CONFIGURE_OPTIONS += --disable-login
$(PKG)_CONFIGURE_OPTIONS += --disable-mesg
$(PKG)_CONFIGURE_OPTIONS += --disable-minix
$(PKG)_CONFIGURE_OPTIONS += --disable-more
$(PKG)_CONFIGURE_OPTIONS += --disable-mount
# mountpoint: enabled when selected or when libblkid requested (both in 2.41 only)
ifeq ($(strip $(FREETZ_UTIL_LINUX_VERSION_2_41)),y)
ifeq ($(or $(strip $(FREETZ_UTIL_LINUX_MOUNTPOINT)),$(strip $(FREETZ_LIB_libblkid))),y)
$(PKG)_CONFIGURE_OPTIONS += --enable-mountpoint
else
$(PKG)_CONFIGURE_OPTIONS += --disable-mountpoint
endif
else
$(PKG)_CONFIGURE_OPTIONS += --disable-mountpoint
endif
$(PKG)_CONFIGURE_OPTIONS += --disable-newgrp
$(PKG)_CONFIGURE_OPTIONS += --disable-nologin
$(PKG)_CONFIGURE_OPTIONS += --disable-nsenter
$(PKG)_CONFIGURE_OPTIONS += --disable-pg
$(PKG)_CONFIGURE_OPTIONS += --disable-pivot_root
$(PKG)_CONFIGURE_OPTIONS += --disable-pylibmount
$(PKG)_CONFIGURE_OPTIONS += --disable-raw
$(PKG)_CONFIGURE_OPTIONS += --disable-rename
$(PKG)_CONFIGURE_OPTIONS += --disable-reset
$(PKG)_CONFIGURE_OPTIONS += --disable-runuser
$(PKG)_CONFIGURE_OPTIONS += --disable-schedutils
$(PKG)_CONFIGURE_OPTIONS += --disable-setpriv
$(PKG)_CONFIGURE_OPTIONS += --disable-setterm
$(PKG)_CONFIGURE_OPTIONS += --disable-su
$(PKG)_CONFIGURE_OPTIONS += --disable-sulogin
$(PKG)_CONFIGURE_OPTIONS += --disable-switch_root
$(PKG)_CONFIGURE_OPTIONS += --disable-tls
$(PKG)_CONFIGURE_OPTIONS += --disable-tunelp
$(PKG)_CONFIGURE_OPTIONS += --disable-ul
$(PKG)_CONFIGURE_OPTIONS += --disable-utmpdump
$(PKG)_CONFIGURE_OPTIONS += --disable-uuidd
$(PKG)_CONFIGURE_OPTIONS += --disable-vipw
$(PKG)_CONFIGURE_OPTIONS += --disable-wall
$(PKG)_CONFIGURE_OPTIONS += --disable-wdctl
$(PKG)_CONFIGURE_OPTIONS += --disable-write
$(PKG)_CONFIGURE_OPTIONS += --disable-zramctl

$(PKG)_CONFIGURE_OPTIONS += --enable-libuuid
$(PKG)_CONFIGURE_OPTIONS += --enable-libblkid

# Shared library variables (util-linux 2.41 only)
# LT version-info:
#   blkid/mount/smartcols/fdisk: 2:0:1 → soname *.so.1 → versioned file *.so.1.1.0
#   lastlog2: 2:0:0 → soname liblastlog2.so.2 → versioned file liblastlog2.so.2.0.0
ifneq ($(strip $(FREETZ_LIB_libblkid)$(FREETZ_LIB_libmount)$(FREETZ_LIB_libsmartcols)$(FREETZ_LIB_libfdisk)$(FREETZ_LIB_liblastlog2)),)
$(PKG)_LIBBLKID_VERSION:=1.1.0
$(PKG)_LIBMOUNT_VERSION:=1.1.0
$(PKG)_LIBSMARTCOLS_VERSION:=1.1.0
$(PKG)_LIBFDISK_VERSION:=1.1.0
$(PKG)_LIBLASTLOG2_VERSION:=2.0.0

$(PKG)_LIBBLKID_BINARY:=$($(PKG)_DIR)/.libs/libblkid.so.$($(PKG)_LIBBLKID_VERSION)
$(PKG)_LIBMOUNT_BINARY:=$($(PKG)_DIR)/.libs/libmount.so.$($(PKG)_LIBMOUNT_VERSION)
$(PKG)_LIBSMARTCOLS_BINARY:=$($(PKG)_DIR)/.libs/libsmartcols.so.$($(PKG)_LIBSMARTCOLS_VERSION)
$(PKG)_LIBFDISK_BINARY:=$($(PKG)_DIR)/.libs/libfdisk.so.$($(PKG)_LIBFDISK_VERSION)
$(PKG)_LIBLASTLOG2_BINARY:=$($(PKG)_DIR)/.libs/liblastlog2.so.$($(PKG)_LIBLASTLOG2_VERSION)

$(PKG)_LIBBLKID_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libblkid.so.$($(PKG)_LIBBLKID_VERSION)
$(PKG)_LIBMOUNT_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmount.so.$($(PKG)_LIBMOUNT_VERSION)
$(PKG)_LIBSMARTCOLS_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libsmartcols.so.$($(PKG)_LIBSMARTCOLS_VERSION)
$(PKG)_LIBFDISK_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libfdisk.so.$($(PKG)_LIBFDISK_VERSION)
$(PKG)_LIBLASTLOG2_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblastlog2.so.$($(PKG)_LIBLASTLOG2_VERSION)

$(PKG)_LIBBLKID_TARGET_BINARY:=$($(PKG)_TARGET_LIBDIR)/libblkid.so.$($(PKG)_LIBBLKID_VERSION)
$(PKG)_LIBMOUNT_TARGET_BINARY:=$($(PKG)_TARGET_LIBDIR)/libmount.so.$($(PKG)_LIBMOUNT_VERSION)
$(PKG)_LIBSMARTCOLS_TARGET_BINARY:=$($(PKG)_TARGET_LIBDIR)/libsmartcols.so.$($(PKG)_LIBSMARTCOLS_VERSION)
$(PKG)_LIBFDISK_TARGET_BINARY:=$($(PKG)_TARGET_LIBDIR)/libfdisk.so.$($(PKG)_LIBFDISK_VERSION)
$(PKG)_LIBLASTLOG2_TARGET_BINARY:=$($(PKG)_TARGET_LIBDIR)/liblastlog2.so.$($(PKG)_LIBLASTLOG2_VERSION)

$(PKG)_LIBS_STAGE_MARKER:=$($(PKG)_DIR)/.libs-staged
endif


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(UTIL_LINUX_DIR) V=1 $(UTIL_LINUX_BINARIES)
	@# When --enable-shared, libtool creates wrapper scripts at top-level; replace
	@# them with the actual ELF binaries from .libs/ (no-op with --enable-shared=no)
	@for b in $(UTIL_LINUX_BINARIES); do \
		[ -f "$(UTIL_LINUX_DIR)/.libs/$$b" ] && \
			cp "$(UTIL_LINUX_DIR)/.libs/$$b" "$(UTIL_LINUX_DIR)/$$b" 2>/dev/null || true; \
	done

# Install binaries with suffix (those that conflict with busybox)
ifneq ($(strip $($(PKG)_BINARIES_WITH_SUFFIX)),)
$($(PKG)_BINARIES_WITH_SUFFIX_TARGET_DIR): $($(PKG)_DEST_DIR)/sbin/%$($(PKG)_BINARIES_SUFFIX): $($(PKG)_DIR)/%
	$(INSTALL_BINARY_STRIP)
endif

# Install binaries without suffix (unique to util-linux)
ifneq ($(strip $($(PKG)_BINARIES_NO_SUFFIX)),)
$($(PKG)_BINARIES_NO_SUFFIX_TARGET_DIR): $($(PKG)_DEST_DIR)/sbin/%: $($(PKG)_DIR)/%
	$(INSTALL_BINARY_STRIP)
endif


# Build, stage, and install selected util-linux shared libraries (version 2.41 only)
ifneq ($(strip $(FREETZ_LIB_libblkid)$(FREETZ_LIB_libmount)$(FREETZ_LIB_libsmartcols)$(FREETZ_LIB_libfdisk)$(FREETZ_LIB_liblastlog2)),)
$($(PKG)_LIBS_STAGE_MARKER): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(UTIL_LINUX_DIR) \
		$(if $(strip $(FREETZ_LIB_libblkid)),libblkid.la) \
		$(if $(strip $(FREETZ_LIB_libmount)),libmount.la) \
		$(if $(strip $(FREETZ_LIB_libsmartcols)),libsmartcols.la) \
		$(if $(strip $(FREETZ_LIB_libfdisk)),libfdisk.la) \
		$(if $(strip $(FREETZ_LIB_liblastlog2)),liblastlog2.la)
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib
	if [ "$(FREETZ_LIB_libblkid)" = "y" ]; then \
		mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/blkid; \
		cp -a $(UTIL_LINUX_DIR)/.libs/libblkid.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/; \
		-cp -a $(UTIL_LINUX_DIR)/.libs/libblkid.a $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ 2>/dev/null; \
		cp -a $(UTIL_LINUX_DIR)/libblkid/src/blkid.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/blkid/blkid.h; \
	fi
	if [ "$(FREETZ_LIB_libmount)" = "y" ]; then \
		mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libmount; \
		cp -a $(UTIL_LINUX_DIR)/.libs/libmount.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/; \
		cp -a $(UTIL_LINUX_DIR)/libmount/src/libmount.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libmount/libmount.h; \
	fi
	if [ "$(FREETZ_LIB_libsmartcols)" = "y" ]; then \
		mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libsmartcols; \
		cp -a $(UTIL_LINUX_DIR)/.libs/libsmartcols.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/; \
		cp -a $(UTIL_LINUX_DIR)/libsmartcols/src/libsmartcols.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libsmartcols/libsmartcols.h; \
	fi
	if [ "$(FREETZ_LIB_libfdisk)" = "y" ]; then \
		mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libfdisk; \
		cp -a $(UTIL_LINUX_DIR)/.libs/libfdisk.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/; \
		cp -a $(UTIL_LINUX_DIR)/libfdisk/src/libfdisk.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libfdisk/libfdisk.h; \
	fi
	if [ "$(FREETZ_LIB_liblastlog2)" = "y" ]; then \
		mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/liblastlog2; \
		cp -a $(UTIL_LINUX_DIR)/.libs/liblastlog2.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/; \
		cp -a $(UTIL_LINUX_DIR)/liblastlog2/src/lastlog2.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/liblastlog2/lastlog2.h; \
	fi
	touch $@

$($(PKG)_LIBBLKID_TARGET_BINARY): $($(PKG)_LIBBLKID_BINARY) $($(PKG)_LIBS_STAGE_MARKER)
	$(INSTALL_LIBRARY_STRIP)

$($(PKG)_LIBMOUNT_TARGET_BINARY): $($(PKG)_LIBMOUNT_BINARY) $($(PKG)_LIBS_STAGE_MARKER)
	$(INSTALL_LIBRARY_STRIP)

$($(PKG)_LIBSMARTCOLS_TARGET_BINARY): $($(PKG)_LIBSMARTCOLS_BINARY) $($(PKG)_LIBS_STAGE_MARKER)
	$(INSTALL_LIBRARY_STRIP)

$($(PKG)_LIBFDISK_TARGET_BINARY): $($(PKG)_LIBFDISK_BINARY) $($(PKG)_LIBS_STAGE_MARKER)
	$(INSTALL_LIBRARY_STRIP)

$($(PKG)_LIBLASTLOG2_TARGET_BINARY): $($(PKG)_LIBLASTLOG2_BINARY) $($(PKG)_LIBS_STAGE_MARKER)
	$(INSTALL_LIBRARY_STRIP)
endif

# Create swapoff symlink to swapon (only for version 2.41)
ifeq ($(strip $(FREETZ_UTIL_LINUX_VERSION_2_41)),y)
ifeq ($(strip $(FREETZ_UTIL_LINUX_SWAPON)),y)
$($(PKG)_DEST_DIR)/sbin/swapoff$($(PKG)_BINARIES_SUFFIX): $($(PKG)_DEST_DIR)/sbin/swapon$($(PKG)_BINARIES_SUFFIX)
	ln -sf $(notdir $<) $@
endif

# blockdev is already installed as blockdev-ng via the with-suffix pattern rule.
# No separate symlink needed.

$(pkg)-precompiled: $($(PKG)_BINARIES_WITH_SUFFIX_TARGET_DIR) $($(PKG)_BINARIES_NO_SUFFIX_TARGET_DIR) $(if $(strip $(FREETZ_UTIL_LINUX_SWAPON)),$($(PKG)_DEST_DIR)/sbin/swapoff$($(PKG)_BINARIES_SUFFIX)) $(if $(strip $(FREETZ_LIB_libblkid)),$($(PKG)_LIBBLKID_TARGET_BINARY)) $(if $(strip $(FREETZ_LIB_libmount)),$($(PKG)_LIBMOUNT_TARGET_BINARY)) $(if $(strip $(FREETZ_LIB_libsmartcols)),$($(PKG)_LIBSMARTCOLS_TARGET_BINARY)) $(if $(strip $(FREETZ_LIB_libfdisk)),$($(PKG)_LIBFDISK_TARGET_BINARY)) $(if $(strip $(FREETZ_LIB_liblastlog2)),$($(PKG)_LIBLASTLOG2_TARGET_BINARY))

$(pkg)-uninstall:
	$(RM) $(UTIL_LINUX_BINARIES_WITH_SUFFIX_TARGET_DIR) $(UTIL_LINUX_BINARIES_NO_SUFFIX_TARGET_DIR)
	$(RM) $(UTIL_LINUX_DEST_DIR)/sbin/swapoff$(UTIL_LINUX_BINARIES_SUFFIX)
	$(RM) $(UTIL_LINUX_DEST_DIR)/sbin/blockdev-ng
	$(RM) $(UTIL_LINUX_TARGET_LIBDIR)/libblkid.so* $(UTIL_LINUX_TARGET_LIBDIR)/libmount.so* $(UTIL_LINUX_TARGET_LIBDIR)/libsmartcols.so* $(UTIL_LINUX_TARGET_LIBDIR)/libfdisk.so* $(UTIL_LINUX_TARGET_LIBDIR)/liblastlog2.so*
else
$(pkg)-precompiled: $($(PKG)_BINARIES_WITH_SUFFIX_TARGET_DIR) $($(PKG)_BINARIES_NO_SUFFIX_TARGET_DIR)

$(pkg)-uninstall:
	$(RM) $(UTIL_LINUX_BINARIES_WITH_SUFFIX_TARGET_DIR) $(UTIL_LINUX_BINARIES_NO_SUFFIX_TARGET_DIR)
	$(RM) $(UTIL_LINUX_DEST_DIR)/sbin/blockdev-ng
endif

$(pkg):

$(pkg)-clean:
	-$(SUBMAKE1) -C $(UTIL_LINUX_DIR) clean
	$(RM) $(UTIL_LINUX_DIR)/.configured
	$(RM) $(UTIL_LINUX_DIR)/.libs-staged
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libblkid.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmount.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libsmartcols.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libfdisk.so* $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblastlog2.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/blkid/blkid.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libmount/libmount.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libsmartcols/libsmartcols.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/libfdisk/libfdisk.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/liblastlog2/lastlog2.h

$(call PKG_ADD_LIB,libblkid)
$(call PKG_ADD_LIB,libmount)
$(call PKG_ADD_LIB,libsmartcols)
$(call PKG_ADD_LIB,libfdisk)
$(call PKG_ADD_LIB,liblastlog2)
$(PKG_FINISH)
