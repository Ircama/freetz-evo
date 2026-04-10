$(call PKG_INIT_BIN, 1.47.4)
$(PKG)_CATEGORY:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=fd5bf388cbdbe006a3d3b318d983b2948382440acc85a87f1e7d108653e8db0b
$(PKG)_SITE:=@SF/e2fsprogs,@KERNEL/linux/kernel/people/tytso/e2fsprogs/v$($(PKG)_VERSION)
### WEBSITE:=https://e2fsprogs.sourceforge.net/
### MANPAGE:=https://www.mankier.com/package/e2fsprogs
### CHANGES:=https://e2fsprogs.sourceforge.net/e2fsprogs-release.html
### CVSREPO:=https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git

$(PKG)_LIBNAMES_SHORT_ALL := com_err e2p ext2fs ss uuid
$(PKG)_LIBNAMES_SHORT :=
$(PKG)_LIBVERSIONS :=
ifeq ($(strip $(FREETZ_LIB_libcom_err)),y)
$(PKG)_LIBNAMES_SHORT += com_err
$(PKG)_LIBVERSIONS += 2.1
endif
ifeq ($(strip $(FREETZ_LIB_libe2p)),y)
$(PKG)_LIBNAMES_SHORT += e2p
$(PKG)_LIBVERSIONS += 2.3
endif
ifeq ($(strip $(FREETZ_LIB_libext2fs)),y)
$(PKG)_LIBNAMES_SHORT += ext2fs
$(PKG)_LIBVERSIONS += 2.4
endif
ifeq ($(strip $(FREETZ_LIB_libss)),y)
$(PKG)_LIBNAMES_SHORT += ss
$(PKG)_LIBVERSIONS += 2.0
endif
ifeq ($(strip $(FREETZ_LIB_libuuid)),y)
$(PKG)_LIBNAMES_SHORT += uuid
$(PKG)_LIBVERSIONS += 1.2
endif

$(PKG)_LIBNAMES_LONG    := $(join $($(PKG)_LIBNAMES_SHORT:%=lib%.so.),$($(PKG)_LIBVERSIONS))
$(PKG)_LIBS_TARGET_DIR  := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_TARGET_LIBDIR)/%)
$(PKG)_LIBS_BUILD_DIR   := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_DIR)/lib/%)
$(PKG)_LIBS_STAGING_DIR := $($(PKG)_LIBNAMES_LONG:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%)

$(PKG)_MAKE_ALL_EXTRAS  := && ln -fsT et $($(PKG)_DIR)/lib/com_err

$(PKG)_BINARIES_ALL := \
	e2fsck fsck \
	mke2fs mklost+found \
	tune2fs dumpe2fs chattr lsattr e2label findfs \
	e2image e2undo debugfs logsave \
	badblocks filefrag e2freefrag uuidd uuidgen \
	resize2fs \
	blkid
$(PKG)_BINARY_SUFFIX := $(if $(FREETZ_PACKAGE_E2FSPROGS_SUFFIX_NG),-ng,)
$(PKG)_BINARIES :=
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2FSCK)),y)
$(PKG)_BINARIES += e2fsck
$(PKG)_MAKE_ALL_EXTRAS += && cp $($(PKG)_DIR)/e2fsck/e2fsck $($(PKG)_DIR)/misc/
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_FSCK)),y)
$(PKG)_BINARIES += fsck
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_MKE2FS)),y)
$(PKG)_BINARIES += mke2fs
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_MKLOSTFOUND)),y)
$(PKG)_BINARIES += mklost+found
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_TUNE2FS)),y)
$(PKG)_BINARIES += tune2fs
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_DUMPE2FS)),y)
$(PKG)_BINARIES += dumpe2fs
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_CHATTR)),y)
$(PKG)_BINARIES += chattr
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_LSATTR)),y)
$(PKG)_BINARIES += lsattr
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2LABEL)),y)
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_FINDFS)),y)
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2IMAGE)),y)
$(PKG)_BINARIES += e2image
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2UNDO)),y)
$(PKG)_BINARIES += e2undo
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_DEBUGFS)),y)
$(PKG)_BINARIES += debugfs
$(PKG)_MAKE_ALL_EXTRAS += && cp $($(PKG)_DIR)/debugfs/debugfs $($(PKG)_DIR)/misc/
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_LOGSAVE)),y)
$(PKG)_BINARIES += logsave
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_BADBLOCKS)),y)
$(PKG)_BINARIES += badblocks
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_FILEFRAG)),y)
$(PKG)_BINARIES += filefrag
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2FREEFRAG)),y)
$(PKG)_BINARIES += e2freefrag
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_UUIDD)),y)
$(PKG)_BINARIES += uuidd
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_UUIDGEN)),y)
$(PKG)_BINARIES += uuidgen
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_RESIZE2FS)),y)
$(PKG)_BINARIES += resize2fs
$(PKG)_MAKE_ALL_EXTRAS += && cp $($(PKG)_DIR)/resize/resize2fs $($(PKG)_DIR)/misc/
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_BLKID)),y)
$(PKG)_BINARIES += blkid
endif
$(PKG)_BINARIES_BUILD_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DIR)/misc/%)
$(PKG)_BINARIES_TARGET_DIR := $(foreach binary,$($(PKG)_BINARIES),$($(PKG)_DEST_DIR)/usr/sbin/$(binary)$($(PKG)_BINARY_SUFFIX))
$(PKG)_BINARIES_SUFFIX_LINKS :=
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2LABEL)),y)
$(PKG)_BINARIES_SUFFIX_LINKS += $($(PKG)_DEST_DIR)/usr/sbin/e2label$($(PKG)_BINARY_SUFFIX)
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_FINDFS)),y)
$(PKG)_BINARIES_SUFFIX_LINKS += $($(PKG)_DEST_DIR)/usr/sbin/findfs$($(PKG)_BINARY_SUFFIX)
endif

$(PKG)_EXCLUDED += $(patsubst %,$($(PKG)_DEST_DIR)/usr/sbin/%,$(filter-out $($(PKG)_BINARIES) $(if $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2LABEL),e2label) $(if $(FREETZ_PACKAGE_E2FSPROGS_TOOL_FINDFS),findfs),$($(PKG)_BINARIES_ALL)))
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_SUFFIX_NG)),y)
$(PKG)_EXCLUDED += $(if $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2FSCK),,usr/sbin/fsck.ext2 usr/sbin/fsck.ext3 usr/sbin/fsck.ext4 usr/sbin/fsck.ext4dev)
$(PKG)_EXCLUDED += $(if $(FREETZ_PACKAGE_E2FSPROGS_TOOL_MKE2FS),,usr/sbin/mkfs.ext2 usr/sbin/mkfs.ext3)
$(PKG)_EXCLUDED += sbin/blkid
else
$(PKG)_EXCLUDED += $(if $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2FSCK),,usr/sbin/fsck.ext2 usr/sbin/fsck.ext3 usr/sbin/fsck.ext4 usr/sbin/fsck.ext4dev)
$(PKG)_EXCLUDED += $(if $(FREETZ_PACKAGE_E2FSPROGS_TOOL_MKE2FS),,usr/sbin/mkfs.ext2 usr/sbin/mkfs.ext3)
$(PKG)_EXCLUDED += $(if $(FREETZ_PACKAGE_E2FSPROGS_BLKID),,sbin/blkid)
endif

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_E2FSPROGS_ALL_DYN
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_E2FSPROGS_PKG_STAT
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_E2FSPROGS_ALL_STAT
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_E2FSPROGS_SUFFIX_NG
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libjemalloc

$(PKG)_DEPENDS_ON += $(if $(FREETZ_LIB_libjemalloc),jemalloc)

ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_SUFFIX_NG)),y)
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_E2FSCK)),y)
$(PKG)_BINARIES_SUFFIX_LINKS += \
	$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext2-ng \
	$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext3-ng \
	$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext4-ng \
	$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext4dev-ng
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_TOOL_MKE2FS)),y)
$(PKG)_BINARIES_SUFFIX_LINKS += \
	$($(PKG)_DEST_DIR)/usr/sbin/mkfs.ext2-ng \
	$($(PKG)_DEST_DIR)/usr/sbin/mkfs.ext3-ng
endif
ifeq ($(strip $(FREETZ_PACKAGE_E2FSPROGS_BLKID)),y)
$(PKG)_BINARIES_SUFFIX_LINKS += $($(PKG)_DEST_DIR)/sbin/blkid-ng
endif
endif

$(PKG)_CONDITIONAL_PATCHES+=current

$(PKG)_CONFIGURE_ENV += ac_cv_path_LDCONFIG=$(TARGET_LDCONFIG)
$(PKG)_CONFIGURE_ENV += gt_cv_func_printf_posix=yes

# uClibc-0.9.29 yields yes, 0.9.28 to be evaluated, it's however absolutely safe to say no
$(PKG)_CONFIGURE_ENV += gt_cv_int_divbyzero_sigfpe=no

# silence some warnings
$(PKG)_CONFIGURE_PRE_CMDS += find $(abspath $($(PKG)_DIR)) -type f -name "*.c" \
	-exec $(SED) -i -r -e 's|(\#define (_LARGEFILE(64)?_SOURCE))|\#ifndef \2\n\1\n\#endif|g' \{\} \+ ;

$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --enable-elf-shlibs
$(PKG)_CONFIGURE_OPTIONS += --enable-libuuid
$(PKG)_CONFIGURE_OPTIONS += --without-libintl-prefix
$(PKG)_CONFIGURE_OPTIONS += --without-libiconv-prefix
$(PKG)_CONFIGURE_OPTIONS += --disable-defrag
$(PKG)_CONFIGURE_OPTIONS += --disable-quota
$(PKG)_CONFIGURE_OPTIONS += --disable-testio-debug
$(PKG)_CONFIGURE_OPTIONS += --disable-backtrace

$(PKG)_LINK_MODE := $(call PKG_SELECTED_SUBOPTIONS,ALL_DYN PKG_STAT ALL_STAT)


ifneq ($(strip $(DL_DIR)/$(E2FSPROGS_SOURCE)),$(strip $(DL_DIR)/$(E2FSPROGS_HOST_SOURCE)))
$(PKG_SOURCE_DOWNLOAD)
endif
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIBS_BUILD_DIR) $($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(E2FSPROGS_DIR) \
		EXTRA_CFLAGS="-ffunction-sections -fdata-sections" \
		EXTRA_LDFLAGS="-Wl,--gc-sections$(if $(FREETZ_LIB_libjemalloc), -ljemalloc)" \
		LINK_MODE=$(E2FSPROGS_LINK_MODE) \
		INFO=true \
		V=1 \
		all \
		$(E2FSPROGS_MAKE_ALL_EXTRAS)

$($(PKG)_LIBS_STAGING_DIR): $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%: $($(PKG)_DIR)/lib/%
	LIBSUBDIR=`echo $(notdir $@) | $(SED) -r -e 's|^lib||g' -e 's|[.]so[.].*$$||g' -e 's|[.]a$$||g'` \
	&& \
	$(SUBMAKE) -C $(E2FSPROGS_DIR)/lib/$${LIBSUBDIR} \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		STRIP=true \
		LDCONFIG=true \
		INFO=true \
		install \
	&& \
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/$${LIBSUBDIR}.pc

$($(PKG)_LIBS_TARGET_DIR): $($(PKG)_TARGET_LIBDIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP)

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/sbin,,$(notdir $(binary))$($(PKG)_BINARY_SUFFIX))))

$($(PKG)_DEST_DIR)/usr/sbin/e2label$($(PKG)_BINARY_SUFFIX): $($(PKG)_DEST_DIR)/usr/sbin/tune2fs$($(PKG)_BINARY_SUFFIX)
	mkdir -p $(dir $@); \
	ln -sf $(notdir $<) $@

$($(PKG)_DEST_DIR)/usr/sbin/findfs$($(PKG)_BINARY_SUFFIX): $($(PKG)_DEST_DIR)/usr/sbin/tune2fs$($(PKG)_BINARY_SUFFIX)
	mkdir -p $(dir $@); \
	ln -sf $(notdir $<) $@

$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext2-ng \
$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext3-ng \
$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext4-ng \
$($(PKG)_DEST_DIR)/usr/sbin/fsck.ext4dev-ng: $($(PKG)_DEST_DIR)/usr/sbin/e2fsck-ng
	mkdir -p $(dir $@); \
	ln -sf e2fsck-ng $@

$($(PKG)_DEST_DIR)/usr/sbin/mkfs.ext2-ng \
$($(PKG)_DEST_DIR)/usr/sbin/mkfs.ext3-ng: $($(PKG)_DEST_DIR)/usr/sbin/mke2fs-ng
	mkdir -p $(dir $@); \
	ln -sf mke2fs-ng $@

$($(PKG)_DEST_DIR)/sbin/blkid-ng: $($(PKG)_DEST_DIR)/usr/sbin/blkid-ng
	mkdir -p $(dir $@); \
	ln -sf ../usr/sbin/blkid-ng $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_LIBS_TARGET_DIR) $($(PKG)_BINARIES_TARGET_DIR) $($(PKG)_BINARIES_SUFFIX_LINKS)


$(pkg)-clean:
	-$(SUBMAKE) -C $(E2FSPROGS_DIR) clean
	$(RM) \
		$(E2FSPROGS_DIR)/lib/com_err $(E2FSPROGS_DIR)/misc/e2fsck \
		$(E2FSPROGS_DIR)/misc/debugfs $(E2FSPROGS_DIR)/misc/resize2fs
	$(RM) \
		$(E2FSPROGS_LIBNAMES_SHORT_ALL:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib%.so*) \
		$(E2FSPROGS_LIBNAMES_SHORT_ALL:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib%.a) \
		$(E2FSPROGS_LIBNAMES_SHORT_ALL:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/lib%_pic.a) \
		$(E2FSPROGS_LIBNAMES_SHORT_ALL:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/%.pc)
	$(RM) -r \
		$(subst com_err,et,$(E2FSPROGS_LIBNAMES_SHORT_ALL:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/%))

$(pkg)-uninstall:
	$(RM) \
		$(E2FSPROGS_LIBNAMES_SHORT_ALL:%=$(E2FSPROGS_TARGET_LIBDIR)/lib%.so*) \
		$(E2FSPROGS_BINARIES_ALL:%=$(E2FSPROGS_DEST_DIR)/usr/sbin/%) \
		$(E2FSPROGS_BINARIES_ALL:%=$(E2FSPROGS_DEST_DIR)/usr/sbin/%-ng) \
		$(E2FSPROGS_DEST_DIR)/usr/sbin/fsck.ext2-ng \
		$(E2FSPROGS_DEST_DIR)/usr/sbin/fsck.ext3-ng \
		$(E2FSPROGS_DEST_DIR)/usr/sbin/fsck.ext4-ng \
		$(E2FSPROGS_DEST_DIR)/usr/sbin/fsck.ext4dev-ng \
		$(E2FSPROGS_DEST_DIR)/usr/sbin/mkfs.ext2-ng \
		$(E2FSPROGS_DEST_DIR)/usr/sbin/mkfs.ext3-ng \
		$(E2FSPROGS_DEST_DIR)/sbin/blkid-ng

$(PKG_FINISH)
