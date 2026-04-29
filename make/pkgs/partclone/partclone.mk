$(call PKG_INIT_BIN, 0.3.31)
$(PKG)_CATEGORY:=Data Migration and Disaster Recovery
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=a6544d8e2490945591df89a7684a063083689f9a525ba135f77802e63659c36e
$(PKG)_SITE:=https://github.com/Thomas-Tsai/partclone/archive/refs/tags
### WEBSITE:=https://github.com/Thomas-Tsai/partclone
### MANPAGE:=https://partclone.org/
### CHANGES:=https://github.com/Thomas-Tsai/partclone/releases
### CVSREPO:=https://github.com/Thomas-Tsai/partclone
### STEWARD:=Ircama

$(PKG)_BINARIES:=partclone.info partclone.dd partclone.restore partclone.chkimg partclone.imager partclone.ntfsfixboot partclone.extfs partclone.xfs partclone.hfsp partclone.apfs partclone.fat partclone.exfat partclone.f2fs partclone.ntfs partclone.btrfs partclone.minix
$(PKG)_BINARIES_BUILD_DIR:=$(addprefix $($(PKG)_DIR)/src/,$($(PKG)_BINARIES))
$(PKG)_BINARIES_TARGET_DIR:=$(addprefix $($(PKG)_DEST_DIR)/usr/sbin/,$($(PKG)_BINARIES))
$(PKG)_ALIASES:=partclone.ext2 partclone.ext3 partclone.ext4 partclone.ext4dev partclone.hfs+ partclone.hfsplus partclone.fat12 partclone.fat16 partclone.fat32 partclone.vfat partclone.ntfsreloc
$(PKG)_ALIASES_TARGET_DIR:=$(addprefix $($(PKG)_DEST_DIR)/usr/sbin/,$($(PKG)_ALIASES))

$(PKG)_DEPENDS_ON += openssl

$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_OPTIONS += --disable-fuse
$(PKG)_CONFIGURE_OPTIONS += --enable-extfs
$(PKG)_CONFIGURE_OPTIONS += --enable-xfs
$(PKG)_CONFIGURE_OPTIONS += --disable-reiserfs
$(PKG)_CONFIGURE_OPTIONS += --disable-reiser4
$(PKG)_CONFIGURE_OPTIONS += --enable-hfsp
$(PKG)_CONFIGURE_OPTIONS += --enable-apfs
$(PKG)_CONFIGURE_OPTIONS += --enable-fat
$(PKG)_CONFIGURE_OPTIONS += --enable-exfat
$(PKG)_CONFIGURE_OPTIONS += --enable-f2fs
$(PKG)_CONFIGURE_OPTIONS += --disable-nilfs2
$(PKG)_CONFIGURE_OPTIONS += --enable-ntfs
$(PKG)_CONFIGURE_OPTIONS += --disable-ufs
$(PKG)_CONFIGURE_OPTIONS += --disable-vmfs
$(PKG)_CONFIGURE_OPTIONS += --disable-jfs
$(PKG)_CONFIGURE_OPTIONS += --enable-btrfs
$(PKG)_CONFIGURE_OPTIONS += --enable-minix
$(PKG)_CONFIGURE_OPTIONS += --enable-ncursesw

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(PARTCLONE_DIR) V=1 all

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/sbin)))

$($(PKG)_DEST_DIR)/usr/sbin/partclone.ext2: $($(PKG)_DEST_DIR)/usr/sbin/partclone.extfs
	ln -sf partclone.extfs $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.ext3: $($(PKG)_DEST_DIR)/usr/sbin/partclone.extfs
	ln -sf partclone.extfs $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.ext4: $($(PKG)_DEST_DIR)/usr/sbin/partclone.extfs
	ln -sf partclone.extfs $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.ext4dev: $($(PKG)_DEST_DIR)/usr/sbin/partclone.extfs
	ln -sf partclone.extfs $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.hfs+: $($(PKG)_DEST_DIR)/usr/sbin/partclone.hfsp
	ln -sf partclone.hfsp $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.hfsplus: $($(PKG)_DEST_DIR)/usr/sbin/partclone.hfsp
	ln -sf partclone.hfsp $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.fat12: $($(PKG)_DEST_DIR)/usr/sbin/partclone.fat
	ln -sf partclone.fat $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.fat16: $($(PKG)_DEST_DIR)/usr/sbin/partclone.fat
	ln -sf partclone.fat $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.fat32: $($(PKG)_DEST_DIR)/usr/sbin/partclone.fat
	ln -sf partclone.fat $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.vfat: $($(PKG)_DEST_DIR)/usr/sbin/partclone.fat
	ln -sf partclone.fat $@

$($(PKG)_DEST_DIR)/usr/sbin/partclone.ntfsreloc: $($(PKG)_DEST_DIR)/usr/sbin/partclone.ntfsfixboot
	ln -sf partclone.ntfsfixboot $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR) $($(PKG)_ALIASES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(PARTCLONE_DIR) clean

$(pkg)-uninstall:
	$(RM) $(PARTCLONE_BINARIES:%=$(PARTCLONE_DEST_DIR)/usr/sbin/%)
	$(RM) $(PARTCLONE_DEST_DIR)/usr/sbin/partclone.ext2 \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.ext3 \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.ext4 \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.ext4dev \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.hfs+ \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.hfsplus \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.fat12 \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.fat16 \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.fat32 \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.vfat \
		$(PARTCLONE_DEST_DIR)/usr/sbin/partclone.ntfsreloc

$(PKG_FINISH)
