$(call PKG_INIT_BIN, 16s)
$(PKG)_SOURCE:=lmon$($(PKG)_VERSION).c
$(PKG)_HASH:=0736ce0f729e48c124a7ba566c069c5a234511cc9c6ac9277da92f8bb44f2b11
$(PKG)_SITE:=@SF/nmon
### WEBSITE:=https://nmon.sourceforge.io/
### MANPAGE:=https://nmon.sourceforge.io/pmwiki.php?n=Site.Documentation
### CHANGES:=https://nmon.sourceforge.io/pmwiki.php?n=Site.Download
### CVSREPO:=https://sourceforge.net/projects/nmon/files/
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/nmon
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/nmon

$(PKG)_DEPENDS_ON += ncurses

# Upstream only enables the generic Linux code paths for X86/ARM.
# Extend those paths to MIPS so the package works on common Freetz targets.
$(PKG)_PATCH_POST_CMDS += perl -0pi -e 's/defined\(X86\) \|\| defined\(ARM\)/defined(X86) || defined(ARM) || defined(MIPS)/g' lmon.c;
# Freetz/uClibc does not ship <fstab.h>, and upstream does not use it anywhere.
$(PKG)_PATCH_POST_CMDS += perl -0pi -e 's/^\x23include <fstab\.h>\n//m' lmon.c;

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86

$(PKG)_ARCH_DEFINE := $(if $(FREETZ_TARGET_ARCH_MIPS),MIPS,$(if $(FREETZ_TARGET_ARCH_ARM),ARM,$(if $(FREETZ_TARGET_ARCH_AARCH64),ARM,$(if $(FREETZ_TARGET_ARCH_X86),X86,))))

define $(PKG)_CUSTOM_UNPACK
	mkdir -p $($(PKG)_DIR); \
	cp $(DL_DIR)/$($(PKG)_SOURCE) $($(PKG)_DIR)/lmon.c
endef

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@test -n "$(NMON_ARCH_DEFINE)" || { echo "Unsupported target architecture for nmon" >&2; exit 1; }
	$(TARGET_CC) $(TARGET_CFLAGS) \
		-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include \
		-D$(NMON_ARCH_DEFINE) \
		$(NMON_DIR)/lmon.c \
		-o $(NMON_BINARY) \
		$(TARGET_LDFLAGS) \
		-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib \
		-lncurses -lm

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(NMON_BINARY) $(NMON_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(NMON_TARGET_BINARY)

$(PKG_FINISH)