$(call TOOLS_INIT, $(if $(FREETZ_TOOLS_FAKEROOT_VERSION_ABANDON),1.38.1,2.1.4))
$(PKG)_SOURCE:=fakeroot_$($(PKG)_VERSION).orig.tar.$(if $(FREETZ_TOOLS_FAKEROOT_VERSION_ABANDON),gz,xz)
$(PKG)_HASH_ABANDON:=37c5063942efe2e2aeefd6e71ae2690bcb9b7d512c53bc6409b54d0730cbdac1
$(PKG)_HASH_CURRENT:=0822bd5a9f0cf19d2ba0546b88b0432d4d3d9917db62c57b74044ccadba06e49
$(PKG)_HASH:=$($(PKG)_HASH_$(if $(FREETZ_TOOLS_FAKEROOT_VERSION_ABANDON),ABANDON,CURRENT))
$(PKG)_SITE:=@DEBIAN/fakeroot
### VERSION:=1.38.1/2.1.4
### WEBSITE:=https://wiki.debian.org/FakeRoot
### MANPAGE:=https://man.archlinux.org/man/fakeroot.1.en
### TRACKER:=https://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=fakeroot;dist=unstable
### CHANGES:=https://launchpad.net/debian/+source/fakeroot/+changelog
### CVSREPO:=https://github.com/openwrt/openwrt/tree/master/tools/fakeroot/patches
### STEWARD:=fda77

$(PKG)_DESTDIR:=$(FREETZ_BASE_DIR)/$(TOOLS_BUILD_DIR)

$(PKG)_MAINARCH_DIR:=$($(PKG)_DIR)/build/arch
$(PKG)_BIARCH_DIR:=$($(PKG)_DIR)/build/biarch

$(PKG)_MAINARCH_LD_PRELOAD_PATH:=$($(PKG)_DESTDIR)/lib
$(PKG)_BIARCH_LD_PRELOAD_PATH:=$($(PKG)_DESTDIR)/lib32
$(PKG)_TARGET_SCRIPT:=$($(PKG)_DESTDIR)/bin/fakeroot
$(PKG)_TARGET_BIARCH_LIB:=$($(PKG)_BIARCH_LD_PRELOAD_PATH)/libfakeroot-0.so

$(PKG)_DEPENDS_ON+=libtool-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_TOOLS_FAKEROOT_VERSION_ABANDON

$(PKG)_CONDITIONAL_PATCHES+=$(if $(FREETZ_TOOLS_FAKEROOT_VERSION_ABANDON),abandon,current)

$(PKG)_CONFIGURE_ENV += ac_cv_header_sys_capability_h=no
$(PKG)_CONFIGURE_ENV += ac_cv_func_capset=n

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += $(if $(findstring Microsoft,$(shell uname -r)),--with-ipc=tcp,--with-ipc=sysv)
$(PKG)_CONFIGURE_OPTIONS += $(QUIET)
$(PKG)_CONFIGURE_OPTIONS += $(SILENT)



# BIARCH means 32-bit libraries on 64-bit hosts
# We need 32-bit fakeroot support if we use the 32-bit mips*-linux-strip during fwmod on a 64-bit host
# The correct condition here would be:
# (using 32-bit [tools/toolchains] [own/dl]) AND (any of the STRIP-options is selected) AND (host is 64-bit)
#BIARCH_BUILD_SYSTEM:=$(filter-out 32,$(HOST_BITNESS))
# replaced by HOST_BIARCH


$(TOOLS_SOURCE_DOWNLOAD)
$(TOOLS_UNPACKED)

$($(PKG)_DIR)/.reconfigured: $($(PKG)_DIR)/.unpacked
ifneq ($(strip $(FREETZ_TOOLS_FAKEROOT_VERSION_ABANDON)),y)
	@$(call _ECHO,reconfiguring)
	cd $(FAKEROOT_HOST_DIR) && $(AUTORECONF)
endif
	touch $@

$($(PKG)_MAINARCH_DIR)/.configured: $($(PKG)_DIR)/.reconfigured
	@$(call _ECHO,configuring)
	(mkdir -p $(FAKEROOT_HOST_MAINARCH_DIR); cd $(FAKEROOT_HOST_MAINARCH_DIR); $(RM) config.cache; \
		CC="$(TOOLS_CC)" \
		CXX="$(TOOLS_CXX)" \
		CFLAGS="$(TOOLS_CFLAGS)" \
		CXXFLAGS="$(TOOLS_CXXFLAGS)" \
		LDFLAGS="$(TOOLS_LDFLAGS)" \
		$(FAKEROOT_HOST_CONFIGURE_ENV) \
		../../configure \
		--prefix=$(FAKEROOT_HOST_DESTDIR) \
		$(FAKEROOT_HOST_CONFIGURE_OPTIONS) \
	);
	touch $@
$($(PKG)_TARGET_SCRIPT): $($(PKG)_MAINARCH_DIR)/.configured
	$(TOOLS_SUBMAKE) -C $(FAKEROOT_HOST_MAINARCH_DIR) install
	$(SED) -i 's,^FAKEROOT_PREFIX=.*,FAKEROOT_PREFIX="$$(readlink -f $$0 | sed "s!/bin/fakeroot\\$$!!")",'  $(FAKEROOT_HOST_TARGET_SCRIPT)
	$(SED) -i 's,^FAKEROOT_BINDIR=.*,FAKEROOT_BINDIR=$${FAKEROOT_PREFIX}/bin,'                              $(FAKEROOT_HOST_TARGET_SCRIPT)
	$(SED) -i 's,^PATHS=.*,PATHS=$${FAKEROOT_PREFIX}/lib:$${FAKEROOT_PREFIX}/lib32,'                        $(FAKEROOT_HOST_TARGET_SCRIPT)

$($(PKG)_BIARCH_DIR)/.configured: $($(PKG)_DIR)/.reconfigured
	@$(call _ECHO,configuring)
	(mkdir -p $(FAKEROOT_HOST_BIARCH_DIR); cd $(FAKEROOT_HOST_BIARCH_DIR); $(RM) config.cache; \
		CC="$(TOOLS_CC)" \
		CXX="$(TOOLS_CXX)" \
		CFLAGS="$(TOOLS_CFLAGS) $(HOST_CFLAGS_FORCE_32BIT_CODE)" \
		CXXFLAGS="$(TOOLS_CXXFLAGS) $(HOST_CFLAGS_FORCE_32BIT_CODE)" \
		LDFLAGS="$(TOOLS_LDFLAGS)" \
		$(FAKEROOT_HOST_CONFIGURE_ENV) \
		../../configure \
		--prefix=$(FAKEROOT_HOST_DESTDIR) \
		$(if $(findstring Microsoft,$(shell uname -r)),--host=$(shell uname -m),) \
		$(FAKEROOT_HOST_CONFIGURE_OPTIONS) \
	);
	touch $@
$($(PKG)_TARGET_BIARCH_LIB): $($(PKG)_BIARCH_DIR)/.configured
	$(TOOLS_SUBMAKE) -C $(FAKEROOT_HOST_BIARCH_DIR) libdir="$(FAKEROOT_HOST_BIARCH_LD_PRELOAD_PATH)" install-libLTLIBRARIES
	touch -c $@

$(pkg)-fixhardcoded:
	-@$(SED) -i "s!$(TOOLS_HARDCODED_DIR)!$(FAKEROOT_HOST_DESTDIR)!g" \
		$(FAKEROOT_HOST_MAINARCH_LD_PRELOAD_PATH)/libfakeroot.la \
		$(FAKEROOT_HOST_BIARCH_LD_PRELOAD_PATH)/libfakeroot.la

$(pkg)-precompiled: $($(PKG)_TARGET_SCRIPT) $(if $(HOST_BIARCH),$($(PKG)_TARGET_BIARCH_LIB))


$(pkg)-clean:
	-$(MAKE) -C $(FAKEROOT_HOST_MAINARCH_DIR) clean
	-$(MAKE) -C $(FAKEROOT_HOST_BIARCH_DIR) clean
	-$(RM) $(FAKEROOT_HOST_DIR)/.{reconfigured,compiled,fixhardcoded}
	-$(RM) $(FAKEROOT_HOST_MAINARCH_DIR)/.{configured,compiled}
	-$(RM) $(FAKEROOT_HOST_BIARCH_DIR)/.{configured,compiled}

$(pkg)-dirclean:
	$(RM) -r $(FAKEROOT_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) -r \
		$(FAKEROOT_HOST_TARGET_SCRIPT) \
		$(FAKEROOT_HOST_DESTDIR)/bin/faked \
		$(FAKEROOT_HOST_DESTDIR)/lib*/libfakeroot*

$(TOOLS_FINISH)
