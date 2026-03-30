$(call PKG_INIT_BIN, 1.0.10)
$(PKG)_CATEGORY:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=2abed61bc6d2b9ec498973c0440b8b804b7a72d7144069b5a9209b2ad693a282
$(PKG)_SITE:=@SF/project/gptfdisk/gptfdisk/$($(PKG)_VERSION)

$(PKG)_BINARIES_ALL := gdisk cgdisk sgdisk fixparts
$(PKG)_BINARIES := $(call PKG_SELECTED_SUBOPTIONS,$($(PKG)_BINARIES_ALL))
$(PKG)_BINARIES_BUILD_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DIR)/%)
$(PKG)_BINARIES_TARGET_DIR := $($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/bin/%)
$(PKG)_EXCLUDED += $(patsubst %,$($(PKG)_DEST_DIR)/usr/bin/%,$(filter-out $($(PKG)_BINARIES),$($(PKG)_BINARIES_ALL)))

# log2/log are provided by libm in uClibc
$(PKG)_PATCH_POST_CMDS += $(SED) -r -i -e 's,(-luuid),\1 -lm,g' Makefile;

$(PKG)_DEPENDS_ON += e2fsprogs
$(PKG)_DEPENDS_ON += $(STDCXXLIB)
ifeq ($(strip $(FREETZ_PACKAGE_GPTFDISK_cgdisk)),y)
$(PKG)_DEPENDS_ON += ncursesw
endif
ifeq ($(strip $(FREETZ_PACKAGE_GPTFDISK_sgdisk)),y)
$(PKG)_DEPENDS_ON += popt
endif
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(GPTFDISK_DIR) $(GPTFDISK_BINARIES) \
		CXX="$(TARGET_CXX)" \
		CXXFLAGS="$(TARGET_CFLAGS) -D_BSD_SOURCE"

$($(PKG)_BINARIES_TARGET_DIR): $($(PKG)_DEST_DIR)/usr/bin/%: $($(PKG)_DIR)/%
	$(INSTALL_BINARY_STRIP)

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(GPTFDISK_DIR) clean

$(pkg)-uninstall:
	$(RM) $(GPTFDISK_BINARIES_ALL:%=$(GPTFDISK_DEST_DIR)/usr/bin/%)

$(PKG_FINISH)
