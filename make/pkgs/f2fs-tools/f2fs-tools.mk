$(call PKG_INIT_BIN, 1.9.0)
$(PKG)_CATEGORY:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=77217562ae7011a6d81b7b3c43c42623db1796a57596408d6c8037def70d6cc7
$(PKG)_SITE:=https://github.com/jaegeuk/f2fs-tools/archive/refs/tags/v$($(PKG)_VERSION)

$(PKG)_CONDITIONAL_PATCHES+=$(if $(FREETZ_TARGET_UCLIBC_0_9_32),uclibc-0.9.32)

$(PKG)_BINARIES_ALL := mkfs.f2fs fsck.f2fs
$(PKG)_BINARIES := $(call PKG_SELECTED_SUBOPTIONS,$($(PKG)_BINARIES_ALL))

# libtool places real ELF binaries in .libs/ subdirectories
$(PKG)_BIN_MKFS_F2FS  := $($(PKG)_DIR)/mkfs/.libs/mkfs.f2fs
$(PKG)_BIN_FSCK_F2FS  := $($(PKG)_DIR)/fsck/.libs/fsck.f2fs
$(PKG)_BINARIES_BUILD_ALL := \
	$($(PKG)_BIN_MKFS_F2FS) \
	$($(PKG)_BIN_FSCK_F2FS)

$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/sbin/%)
$(PKG)_EXCLUDED += $(patsubst %,$($(PKG)_DEST_DIR)/usr/sbin/%,$(filter-out $($(PKG)_BINARIES),$($(PKG)_BINARIES_ALL)))

$(PKG)_DEPENDS_ON += e2fsprogs
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_ENV += ac_cv_search_uuid_generate="-luuid"
$(PKG)_CONFIGURE_ENV += ac_cv_file__git=no

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_ALL): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(F2FS_TOOLS_DIR) V=1 all

$($(PKG)_DEST_DIR)/usr/sbin/mkfs.f2fs: $($(PKG)_BIN_MKFS_F2FS)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/sbin/fsck.f2fs: $($(PKG)_BIN_FSCK_F2FS)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(F2FS_TOOLS_DIR) clean

$(pkg)-uninstall:
	$(RM) $(F2FS_TOOLS_BINARIES_ALL:%=$(F2FS_TOOLS_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
