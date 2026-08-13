$(call PKG_INIT_BIN, 4.2)
$(PKG)_CATEGORY_PKGS:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=64926eebf90092dca21b14259a5301b7b98e7b1943e8a201c7d726084809b527
$(PKG)_SITE:=https://github.com/dosfstools/dosfstools/releases/download/v$($(PKG)_VERSION)

$(PKG)_BINARIES_ALL := fsck.fat fatlabel mkfs.fat
$(PKG)_BINARIES := $(call PKG_SELECTED_SUBOPTIONS,$($(PKG)_BINARIES_ALL))
$(PKG)_BINARIES_BUILD_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DIR)/src/%)
$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/sbin/%)
$(PKG)_EXCLUDED += $(patsubst %,$($(PKG)_DEST_DIR)/usr/sbin/%,$(filter-out $($(PKG)_BINARIES),$($(PKG)_BINARIES_ALL)))

ifeq ($(strip $(FREETZ_TARGET_UCLIBC_0_9_28)),y)
$(PKG)_DEPENDS_ON += iconv
$(PKG)_CONFIGURE_ENV += LIBS="-liconv"
endif

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(DOSFSTOOLS_DIR) \
		V=1 \
		all

$($(PKG)_BINARIES_TARGET_DIR): $($(PKG)_DEST_DIR)/usr/sbin/%: $($(PKG)_DIR)/src/%
	$(INSTALL_BINARY_STRIP)

$(pkg):

# Create fsck.vfat symlink -> fsck.fat in /usr/sbin/ (needed by fsck wrapper)
ifeq ($(strip $(FREETZ_PACKAGE_DOSFSTOOLS_fsck_fat)),y)
$($(PKG)_DEST_DIR)/usr/sbin/fsck.vfat: $($(PKG)_DEST_DIR)/usr/sbin/fsck.fat
	ln -sf fsck.fat $@
endif

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR) \
	$(if $(filter y,$(FREETZ_PACKAGE_DOSFSTOOLS_fsck_fat)),$($(PKG)_DEST_DIR)/usr/sbin/fsck.vfat)

$(pkg)-clean:
	-$(SUBMAKE) -C $(DOSFSTOOLS_DIR) clean

$(pkg)-uninstall:
	$(RM) $(DOSFSTOOLS_BINARIES_ALL:%=$(DOSFSTOOLS_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
