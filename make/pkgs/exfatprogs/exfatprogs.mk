$(call PKG_INIT_BIN, 1.3.2)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=67ddb50543636292df8fde58117eefd54210d6cd7bf1eea5e91d2c4dccbc425e
$(PKG)_SITE:=https://github.com/exfatprogs/exfatprogs/releases/download/$($(PKG)_VERSION)

$(PKG)_CONDITIONAL_PATCHES+=uclibc-0.9.32

$(PKG)_BINARIES_ALL := mkfs.exfat fsck.exfat exfatlabel tune.exfat
$(PKG)_BINARIES := $(call PKG_SELECTED_SUBOPTIONS,$($(PKG)_BINARIES_ALL))

$(PKG)_BIN_MKFS_EXFAT := $($(PKG)_DIR)/mkfs/mkfs.exfat
$(PKG)_BIN_FSCK_EXFAT := $($(PKG)_DIR)/fsck/fsck.exfat
$(PKG)_BIN_EXFATLABEL := $($(PKG)_DIR)/label/exfatlabel
$(PKG)_BIN_TUNE_EXFAT := $($(PKG)_DIR)/tune/tune.exfat
$(PKG)_BINARIES_BUILD_ALL := \
	$($(PKG)_BIN_MKFS_EXFAT) \
	$($(PKG)_BIN_FSCK_EXFAT) \
	$($(PKG)_BIN_EXFATLABEL) \
	$($(PKG)_BIN_TUNE_EXFAT)

$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/sbin/%)
$(PKG)_EXCLUDED += $(patsubst %,$($(PKG)_DEST_DIR)/usr/sbin/%,$(filter-out $($(PKG)_BINARIES),$($(PKG)_BINARIES_ALL)))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_ALL): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(EXFATPROGS_DIR) \
		V=1 \
		all

$($(PKG)_DEST_DIR)/usr/sbin/mkfs.exfat: $($(PKG)_BIN_MKFS_EXFAT)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/sbin/fsck.exfat: $($(PKG)_BIN_FSCK_EXFAT)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/sbin/exfatlabel: $($(PKG)_BIN_EXFATLABEL)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/sbin/tune.exfat: $($(PKG)_BIN_TUNE_EXFAT)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(EXFATPROGS_DIR) clean

$(pkg)-uninstall:
	$(RM) $(EXFATPROGS_BINARIES_ALL:%=$(EXFATPROGS_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
