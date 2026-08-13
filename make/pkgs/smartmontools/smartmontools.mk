$(call PKG_INIT_BIN, $(if $(FREETZ_PACKAGE_SMARTMONTOOLS_VERSION_ABANDON),7.2,7.5))
# smartmontools 7.5 is built as C++11; its configure checks -std=c++11 and
# -std=gnu++11, which the old GCC 4.6.4 toolchain rejects ("cc1plus: error:
# unrecognized command line option '-std=c++11'"), so the 7.5 version is gated
# on FREETZ_TARGET_GCC_4_7_MIN in Config.in (7.2 is selected on older toolchains).
# NOT a uClibc gate: uClibc 1.0.14 with GCC 5.5 supports C++11 and builds fine
# (no regression on any uClibc >= 1.0.58 toolchain either).
$(PKG)_CATEGORY_PKGS:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH_ABANDON:=5cd98a27e6393168bc6aaea070d9e1cd551b0f898c52f66b2ff2e5d274118cd6
$(PKG)_HASH_CURRENT:=690b83ca331378da9ea0d9d61008c4b22dde391387b9bbad7f29387f2595f76e
$(PKG)_HASH:=$($(PKG)_HASH_$(if $(FREETZ_PACKAGE_SMARTMONTOOLS_VERSION_ABANDON),ABANDON,CURRENT))
$(PKG)_SITE:=@SF/smartmontools
### WEBSITE:=https://www.smartmontools.org/
### MANPAGE:=https://www.smartmontools.org/wiki/TocDoc
### CHANGES:=https://github.com/smartmontools/smartmontools/releases
### CVSREPO:=https://www.smartmontools.org/timeline
### STEWARD:=fda77

$(PKG)_BINARIES := smartctl
$(PKG)_BINARIES_BUILD_DIR := $(addprefix $($(PKG)_DIR)/,$($(PKG)_BINARIES))
$(PKG)_BINARIES_TARGET_DIR := $(addprefix $($(PKG)_DEST_DIR)/usr/sbin/,$($(PKG)_BINARIES))

$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

$(PKG)_CONDITIONAL_PATCHES+=$(if $(FREETZ_PACKAGE_SMARTMONTOOLS_VERSION_ABANDON),abandon,current)
$(PKG)_CONDITIONAL_PATCHES+=$(if $(FREETZ_PACKAGE_SMARTMONTOOLS_VERSION_ABANDON),abandon,current)/$(if $(FREETZ_SYSTEM_TYPE_PUMA6),puma,mips)

$(PKG)_CONFIGURE_OPTIONS += --without-gnupg
$(PKG)_CONFIGURE_OPTIONS += --without-selinux
$(PKG)_CONFIGURE_OPTIONS += --without-libcap-ng
$(PKG)_CONFIGURE_OPTIONS += --without-libsystemd
$(PKG)_CONFIGURE_OPTIONS += --without-nvme-devicescan
ifeq ($(strip $(FREETZ_PACKAGE_SMARTMONTOOLS_VERSION_ABANDON)),y)
$(PKG)_CONFIGURE_OPTIONS += --without-cxx11-option
endif


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(SMARTMONTOOLS_DIR)

$($(PKG)_BINARIES_TARGET_DIR): $($(PKG)_DEST_DIR)/usr/sbin/%: $($(PKG)_DIR)/%
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)


$(pkg)-clean:
	-$(SUBMAKE) -C $(SMARTMONTOOLS_DIR) clean

$(pkg)-uninstall:
	$(RM) $(SMARTMONTOOLS_BINARIES_TARGET_DIR)

$(PKG_FINISH)

