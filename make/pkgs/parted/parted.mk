$(call PKG_INIT_BIN, 3.6)
$(PKG)_CATEGORY:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=3b43dbe33cca0f9a18601ebab56b7852b128ec1a3df3a9b30ccde5e73359e612
$(PKG)_SITE:=@GNU/$(pkg)
### WEBSITE:=https://www.gnu.org/software/parted/
### MANPAGE:=https://www.gnu.org/software/parted/manual/
### CHANGES:=https://git.savannah.gnu.org/cgit/parted.git/tree/NEWS
### CVSREPO:=https://git.savannah.gnu.org/cgit/parted.git
### STEWARD:=Ircama

$(PKG)_CONDITIONAL_PATCHES+=$(if $(and $(FREETZ_TARGET_ARCH_MIPS),$(FREETZ_TARGET_GCC_4_6),$(FREETZ_TARGET_UCLIBC_0_9_32)),gcc-4.6-uclibc-0.9.32)

$(PKG)_BINARIES_ALL := parted partprobe
$(PKG)_BINARIES := $(call PKG_SELECTED_SUBOPTIONS,$($(PKG)_BINARIES_ALL))
$(PKG)_BINARIES_BUILD_DIR := $(addprefix $($(PKG)_DIR)/,$(join $($(PKG)_BINARIES:%=%/),$($(PKG)_BINARIES)))
$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/sbin/%)
$(PKG)_EXCLUDED += $(patsubst %,$($(PKG)_DEST_DIR)/usr/sbin/%,$(filter-out $($(PKG)_BINARIES),$($(PKG)_BINARIES_ALL)))

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libjemalloc

$(PKG)_DEPENDS_ON += e2fsprogs jemalloc

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)
$(PKG)_CONFIGURE_ENV += LDFLAGS="$(TARGET_LDFLAGS) -L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -ljemalloc"

$(PKG)_CONFIGURE_OPTIONS += --enable-shared=no
$(PKG)_CONFIGURE_OPTIONS += --enable-static=yes
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --disable-device-mapper
$(PKG)_CONFIGURE_OPTIONS += --without-readline
$(PKG)_CONFIGURE_OPTIONS += --disable-debug

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$(PKG)_STAGING_MARKER:=$($(PKG)_DIR)/.staged

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(PARTED_DIR) V=1 all

$($(PKG)_STAGING_MARKER): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(PARTED_DIR) V=1 all
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/parted
	mkdir -p $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib
	cp -a $(PARTED_DIR)/include/parted/*.h $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/parted/
	cp -a $(PARTED_DIR)/libparted/.libs/libparted.a $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ 2>/dev/null || true
	cp -a $(PARTED_DIR)/libparted/fs/.libs/libparted-fs-resize.a $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ 2>/dev/null || true
	# libparted links blkid symbols; stage libblkid.a from e2fsprogs build
	@for d in $(SOURCE_DIR)/e2fsprogs-*/lib; do \
		[ -f "$$d/libblkid.a" ] && cp -a "$$d/libblkid.a" $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ && break; \
	done; true
	touch $@

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/sbin)))

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR) $($(PKG)_STAGING_MARKER)

$(pkg)-clean:
	-$(SUBMAKE) -C $(PARTED_DIR) clean
	$(RM) $(PARTED_DIR)/.staged
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/parted
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libparted.a
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libparted-fs-resize.a
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libblkid.a

$(pkg)-uninstall:
	$(RM) $(PARTED_BINARIES_ALL:%=$(PARTED_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
