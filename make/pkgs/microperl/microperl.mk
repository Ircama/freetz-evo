# partly taken from www.buildroot.org
$(call PKG_INIT_BIN, $(if $(FREETZ_PACKAGE_MICROPERL_VERSION_5_10),5.10.1,5.38.2))
$(PKG)_SOURCE:=perl-$($(PKG)_VERSION).tar$(if $(FREETZ_PACKAGE_MICROPERL_VERSION_5_10),.bz2,.xz)
$(PKG)_HASH_5_10:=9385f2c8c2ca8b1dc4a7c31903f1f8dc8f2ba867dc2a9e5c93012ed6b564e826
$(PKG)_HASH_5_38:=d91115e90b896520e83d4de6b52f8254ef2b70a8d545ffab33200ea9f1cf29e8
$(PKG)_HASH:=$($(PKG)_HASH_$(subst .,_,$(call GET_MAJOR_VERSION,$($(PKG)_VERSION),2)))
$(PKG)_SITE:=https://www.cpan.org/src/5.0

$(PKG)_BINARY:=$($(PKG)_DIR)/microperl
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/microperl
$(PKG)_TARGET_SYMLINK:=$($(PKG)_DEST_DIR)/usr/bin/perl
$(PKG)_TARGET_MODULES:=$($(PKG)_TARGET_DIR)/.modules_installed
$(PKG)_TARGET_MODULES_DIR:=$($(PKG)_DEST_DIR)/usr/lib/perl5/$($(PKG)_VERSION)
$(PKG)_TARGET_MODS:=$(subst ",,$(FREETZ_PACKAGE_MICROPERL_MODULES))

$(PKG)_DEPENDS_ON += wget-host

$(PKG)_CONDITIONAL_PATCHES+=$(if $(FREETZ_PACKAGE_MICROPERL_VERSION_5_10),5.10,5.38)

$(PKG)_PATCH_PRE_CMDS += chmod -R u+w .;
ifeq ($(FREETZ_PACKAGE_MICROPERL_VERSION_5_38),y)
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/uuudmap.h) $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/ubitcount.h) $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/umg_data.h) .;
$(PKG)_PATCH_POST_CMDS += sh $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/apply_stubs.sh);
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/Errno.pm) lib/;
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/Storable.pm) lib/;
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/POSIX.pm) lib/;
$(PKG)_PATCH_POST_CMDS += cp -f dist/Exporter/lib/Exporter.pm lib/;
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/constant.pm) lib/;
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/Carp.pm) lib/;
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/Fcntl.pm) lib/;
$(PKG)_PATCH_POST_CMDS += mkdir -p lib/Exporter && cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/Exporter/Heavy.pm) lib/Exporter/;
$(PKG)_PATCH_POST_CMDS += cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/feature.pm) lib/;
$(PKG)_PATCH_POST_CMDS += mkdir -p lib/File && cp -f $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/File/Basename.pm) lib/File/;
$(PKG)_PATCH_POST_CMDS += sh $(abspath $(dir $(lastword $(MAKEFILE_LIST)))patches/5.38/apply_host_modules.sh);
endif
$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(MICROPERL_DIR) -f Makefile.micro \
		CC="$(TARGET_CC)" OPTIMIZE="$(TARGET_CFLAGS) -ffunction-sections -fdata-sections" LDFLAGS="-Wl,--gc-sections"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)
	ln -fs microperl $(MICROPERL_TARGET_SYMLINK)

$($(PKG)_TARGET_MODULES): $($(PKG)_DIR)/.unpacked
	mkdir -p $(MICROPERL_TARGET_MODULES_DIR)
	cp -dpfR $(MICROPERL_DIR)/lib/* $(MICROPERL_TARGET_MODULES_DIR)/
	touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_TARGET_MODULES)

$(pkg)-clean:
	-$(SUBMAKE) -C $(MICROPERL_DIR) -f Makefile.micro clean
	-$(RM) $(MICROPERL_TARGET_SYMLINK)
	-$(RM) -r $(MICROPERL_TARGET_MODULES_DIR)
	-$(RM) $(MICROPERL_TARGET_MODULES)

$(pkg)-uninstall:
	$(RM) $(MICROPERL_TARGET_BINARY)
	$(RM) $(MICROPERL_TARGET_SYMLINK)
	$(RM) -r $(MICROPERL_TARGET_MODULES_DIR)

$(PKG_FINISH)
