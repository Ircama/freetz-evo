$(call TOOLS_INIT, $(if $(FREETZ_TOOLS_PATCHELF_VERSION_ABANDON),0.14.5,0.19.3))
$(PKG)_SOURCE:=patchelf-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH_ABANDON:=b9a46f2989322eb89fa4f6237e20836c57b455aa43a32545ea093b431d982f5c
$(PKG)_HASH_CURRENT:=20dbe23e9dbc4ad769078a867ad002c04297a069ff93c95fb72242dd55d4dd6f
$(PKG)_HASH:=$($(PKG)_HASH_$(if $(FREETZ_TOOLS_PATCHELF_VERSION_ABANDON),ABANDON,CURRENT))
$(PKG)_SITE:=https://github.com/NixOS/patchelf/releases/download/$($(PKG)_VERSION)
### VERSION:=0.14.5/0.19.3
### WEBSITE:=https://opencollective.com/nixos
### MANPAGE:=https://sources.debian.org/patches/patchelf/
### CHANGES:=https://github.com/NixOS/patchelf/releases
### CVSREPO:=https://github.com/NixOS/patchelf
### STEWARD:=fda77

$(PKG)_SRC_BINARY := $($(PKG)_DIR)/src/patchelf
$(PKG)_DST_BINARY := $(TOOLS_DIR)/patchelf

$(PKG)_CONDITIONAL_PATCHES+=$(if $(FREETZ_TOOLS_PATCHELF_VERSION_ABANDON),abandon,current)
$(PKG)_REBUILD_SUBOPTS += FREETZ_TOOLS_PATCHELF_VERSION_ABANDON

$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)
$(TOOLS_CONFIGURED_CONFIGURE)

$($(PKG)_SRC_BINARY): $($(PKG)_DIR)/.configured
	$(TOOLS_SUBMAKE) -C $(PATCHELF_HOST_DIR) all

$($(PKG)_DST_BINARY): $($(PKG)_SRC_BINARY)
	$(INSTALL_FILE)

$(pkg)-precompiled: $($(PKG)_DST_BINARY)

$(TOOLS_DIR)/patchelf-target: $($(PKG)_DST_BINARY)
	$(INSTALL_FILE)

.PHONY: patchelf-target-host
patchelf-target-host: $(TOOLS_DIR)/patchelf-target


$(pkg)-clean:
	-$(MAKE) -C $(PATCHELF_HOST_DIR) clean

$(pkg)-dirclean:
	$(RM) -r $(PATCHELF_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(PATCHELF_HOST_DST_BINARY)
	$(RM) $(TOOLS_DIR)/patchelf-target

$(TOOLS_FINISH)
