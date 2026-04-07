$(call PKG_INIT_BIN, 0.3.31)
$(PKG)_CATEGORY:=Disk Clone
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=a6544d8e2490945591df89a7684a063083689f9a525ba135f77802e63659c36e
$(PKG)_SITE:=https://github.com/Thomas-Tsai/partclone/archive/refs/tags
### WEBSITE:=https://github.com/Thomas-Tsai/partclone
### MANPAGE:=https://partclone.org/
### CHANGES:=https://github.com/Thomas-Tsai/partclone/releases
### CVSREPO:=https://github.com/Thomas-Tsai/partclone

$(PKG)_BINARIES:=partclone.info partclone.dd partclone.restore partclone.chkimg partclone.imager partclone.ntfsfixboot
$(PKG)_BINARIES_BUILD_DIR:=$(addprefix $($(PKG)_DIR)/src/,$($(PKG)_BINARIES))
$(PKG)_BINARIES_TARGET_DIR:=$(addprefix $($(PKG)_DEST_DIR)/usr/sbin/,$($(PKG)_BINARIES))

$(PKG)_DEPENDS_ON += openssl

$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_OPTIONS += --disable-fuse
$(PKG)_CONFIGURE_OPTIONS += --disable-extfs
$(PKG)_CONFIGURE_OPTIONS += --disable-xfs
$(PKG)_CONFIGURE_OPTIONS += --disable-reiserfs
$(PKG)_CONFIGURE_OPTIONS += --disable-reiser4
$(PKG)_CONFIGURE_OPTIONS += --disable-hfsp
$(PKG)_CONFIGURE_OPTIONS += --disable-apfs
$(PKG)_CONFIGURE_OPTIONS += --disable-fat
$(PKG)_CONFIGURE_OPTIONS += --disable-exfat
$(PKG)_CONFIGURE_OPTIONS += --disable-f2fs
$(PKG)_CONFIGURE_OPTIONS += --disable-nilfs2
$(PKG)_CONFIGURE_OPTIONS += --disable-ntfs
$(PKG)_CONFIGURE_OPTIONS += --disable-ufs
$(PKG)_CONFIGURE_OPTIONS += --disable-vmfs
$(PKG)_CONFIGURE_OPTIONS += --disable-jfs
$(PKG)_CONFIGURE_OPTIONS += --disable-btrfs
$(PKG)_CONFIGURE_OPTIONS += --disable-minix
$(PKG)_CONFIGURE_OPTIONS += --disable-ncursesw

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(PARTCLONE_DIR) V=1 all

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/sbin)))

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(PARTCLONE_DIR) clean

$(pkg)-uninstall:
	$(RM) $(PARTCLONE_BINARIES:%=$(PARTCLONE_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
