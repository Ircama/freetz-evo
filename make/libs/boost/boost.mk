# Boost 1.87.0: the complete header tree plus the Boost.Thread and Boost.System
# shared libraries, cross-built with b2 for the target.
#
# The b2 cross-build follows the pattern already used in this tree by
# pdns-recursor / pdns-authoritative / pdns-dnsdist (which build their bundled
# Boost from source): a user-config.jam with "using gcc : : $(TARGET_CXX)"
# plus the per-architecture b2 properties from config/mod/boost.in
# (FREETZ_TARGET_B2_ARCH_OPTS).
#
# Consumers use the CMake package config, e.g.
#     find_package(Boost CONFIG REQUIRED COMPONENTS thread)
# CMake 4.x no longer ships FindBoost (module mode), so a minimal
# BoostConfig.cmake (files/cmake/*.cmake) is installed into the staging
# prefix. It provides exactly the components built here: thread and system.
$(call PKG_INIT_LIB, 1.87.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY_LIBS:=General

$(PKG)_SOURCE_DOWNLOAD_NAME:=boost_$(subst .,_,$($(PKG)_VERSION)).tar.bz2
$(PKG)_SOURCE:=$(pkg)-$(subst .,_,$($(PKG)_VERSION)).tar.bz2
$(PKG)_HASH:=af57be25cb4c4f4b413ed692fe378affb4352ea50fbe294a11ef548f4d527d89
$(PKG)_SITE:=https://archives.boost.io/release/$($(PKG)_VERSION)/source
### WEBSITE:=https://www.boost.org/
### CHANGES:=https://www.boost.org/users/history/
### CVSREPO:=https://github.com/boostorg/boost

$(PKG)_LIB_VERSION:=$($(PKG)_VERSION)
$(PKG)_LIB_THREAD:=libboost_thread.so.$($(PKG)_LIB_VERSION)
$(PKG)_LIB_SYSTEM:=libboost_system.so.$($(PKG)_LIB_VERSION)

$(PKG)_BINARY:=$($(PKG)_DIR)/stage/lib/$($(PKG)_LIB_THREAD)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/$($(PKG)_LIB_THREAD)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/$($(PKG)_LIB_THREAD)
$(PKG)_BINARY_SYSTEM:=$($(PKG)_DIR)/stage/lib/$($(PKG)_LIB_SYSTEM)
$(PKG)_STAGING_BINARY_SYSTEM:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/$($(PKG)_LIB_SYSTEM)
$(PKG)_TARGET_BINARY_SYSTEM:=$($(PKG)_TARGET_DIR)/$($(PKG)_LIB_SYSTEM)

$(PKG)_BOOTSTRAP:=$($(PKG)_DIR)/.bootstrap
$(PKG)_BUILT:=$($(PKG)_DIR)/.built
$(PKG)_STAGED:=$($(PKG)_DIR)/.staged
$(PKG)_STAGING_CMAKE_DIR:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/cmake/Boost-$($(PKG)_LIB_VERSION)

# b2 library selection: thread needs pthread (nptl); system is provided for
# consumers that link Boost.System explicitly.
$(PKG)_B2_LIBRARIES:=thread,system
$(PKG)_B2_ARCH_OPTS:=$(subst ",,$(FREETZ_TARGET_B2_ARCH_OPTS))
$(PKG)_B2_TAILFLAGS:=target-os=linux variant=release threading=multi cxxstd=17 --layout=system

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# b2 is a build host tool: it must be bootstrapped with the *host* compiler,
# never with the cross compiler from $(TARGET_CONFIGURE_ENV).
$(BOOST_BOOTSTRAP): $(BOOST_DIR)/.unpacked
	@$(call _ECHO,bootstrapping)
	cd $(BOOST_DIR) && CC=gcc CXX=g++ ./bootstrap.sh --with-libraries=$(BOOST_B2_LIBRARIES) $(SILENT)
	@touch $@

$(BOOST_BUILT): $(BOOST_BOOTSTRAP) $(MAKE_DIR)/libs/boost/boost.mk
	@$(call _ECHO,building)
	printf 'using gcc : : $(TARGET_CXX) : <archiver>$(TARGET_AR) <ranlib>$(TARGET_RANLIB) <compileflags>"$(TARGET_CFLAGS) -fPIC" <linkflags>"$(TARGET_LDFLAGS)" ;\n' \
		> $(BOOST_DIR)/user-config.jam
	cd $(BOOST_DIR) && ./b2 --user-config=$$(pwd)/user-config.jam toolset=gcc \
		$(BOOST_B2_ARCH_OPTS) $(BOOST_B2_TAILFLAGS) link=shared runtime-link=shared stage $(SILENT)
	@touch $@

$(BOOST_BINARY) $(BOOST_BINARY_SYSTEM): $(BOOST_BUILT) ;

$(BOOST_STAGED): $(BOOST_BUILT)
	@$(call _ECHO,staging)
	cd $(BOOST_DIR) && ./b2 --user-config=$$(pwd)/user-config.jam toolset=gcc \
		$(BOOST_B2_ARCH_OPTS) $(BOOST_B2_TAILFLAGS) link=shared runtime-link=shared \
		--prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr install $(SILENT)
	mkdir -p $(BOOST_STAGING_CMAKE_DIR)
	cp $(BOOST_MAKE_DIR)/files/cmake/*.cmake $(BOOST_STAGING_CMAKE_DIR)/
	@touch $@

$(BOOST_STAGING_BINARY) $(BOOST_STAGING_BINARY_SYSTEM): $(BOOST_STAGED) ;

$(BOOST_TARGET_BINARY): $(BOOST_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(BOOST_TARGET_BINARY_SYSTEM): $(BOOST_STAGING_BINARY_SYSTEM)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $(BOOST_STAGING_BINARY)

$(pkg)-precompiled: $(BOOST_TARGET_BINARY) $(BOOST_TARGET_BINARY_SYSTEM)

$(pkg)-clean:
	$(RM) -r $(BOOST_DIR)/stage $(BOOST_DIR)/bin.v2 $(BOOST_BUILT) $(BOOST_STAGED) $(BOOST_BOOTSTRAP)

$(pkg)-uninstall:
	$(RM) $(BOOST_TARGET_BINARY) $(BOOST_TARGET_BINARY_SYSTEM)

$(PKG_FINISH)
