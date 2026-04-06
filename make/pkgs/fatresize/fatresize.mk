$(call PKG_INIT_BIN, 20260403)
$(PKG)_CATEGORY:=Disk Tools
$(PKG)_GIT_COMMIT:=75cbc388dc7fc6add789812a3f7ddaead2d44379
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_GIT_COMMIT).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=c369a5806cafb144147f72165db8c2d482368f380e2aaf735475de7802b038a7
$(PKG)_SITE:=https://github.com/ya-mouse/fatresize/archive
$(PKG)_DIR:=$(SOURCE_DIR)/fatresize-$($(PKG)_GIT_COMMIT)
### WEBSITE:=https://github.com/ya-mouse/fatresize
### MANPAGE:=https://github.com/ya-mouse/fatresize/blob/master/README
### CHANGES:=https://github.com/ya-mouse/fatresize/commits/master
### CVSREPO:=https://github.com/ya-mouse/fatresize

$(PKG)_BINARY:=$($(PKG)_DIR)/fatresize
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/sbin/fatresize

$(PKG)_DEPENDS_ON += parted e2fsprogs

# fatresize's configure checks parted headers before pkg-config macros.
$(PKG)_CONFIGURE_ENV += CFLAGS="$(TARGET_CFLAGS) -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
# Cross-compile probe may otherwise set this to "no", which would later
# produce an invalid -D_FILE_OFFSET_BITS=no define.
$(PKG)_CONFIGURE_ENV += ac_cv_sys_file_offset_bits=64
$(PKG)_CONFIGURE_ENV += PARTED_CFLAGS="-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
# configure adds -lparted-fs-resize itself for libparted >= 3.1.
# Keep only base libs/path here to avoid duplicate symbols from static archives.
$(PKG)_CONFIGURE_ENV += PARTED_LIBS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -lparted -luuid -ldl"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	# Build only the binary target (no manpage tool dependency) and allow
	# duplicate symbols from libparted/libparted-fs-resize static archives.
	$(SUBMAKE) -C $(FATRESIZE_DIR) V=1 LDFLAGS="$(TARGET_LDFLAGS) -Wl,--allow-multiple-definition" fatresize

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(FATRESIZE_DIR) clean

$(pkg)-uninstall:
	$(RM) $(FATRESIZE_TARGET_BINARY)

$(PKG_FINISH)
