$(call PKG_INIT_BIN, 3.6)
$(PKG)_CATEGORY:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=3b43dbe33cca0f9a18601ebab56b7852b128ec1a3df3a9b30ccde5e73359e612
$(PKG)_SITE:=@GNU/$(pkg)
### WEBSITE:=https://www.gnu.org/software/parted/
### MANPAGE:=https://www.gnu.org/software/parted/manual/
### CHANGES:=https://git.savannah.gnu.org/cgit/parted.git/tree/NEWS
### CVSREPO:=https://git.savannah.gnu.org/cgit/parted.git

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

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(PARTED_DIR) V=1 all

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/sbin)))

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(PARTED_DIR) clean

$(pkg)-uninstall:
	$(RM) $(PARTED_BINARIES_ALL:%=$(PARTED_DEST_DIR)/usr/sbin/%)

$(PKG_FINISH)
