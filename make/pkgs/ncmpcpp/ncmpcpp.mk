$(call PKG_INIT_BIN, 0.10.1)
$(PKG)_CATEGORY:=Audio
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ddc89da86595d272282ae8726cc7913867b9517eec6e765e66e6da860b58e2f9
$(PKG)_SITE:=https://github.com/ncmpcpp/ncmpcpp/archive/refs/tags
### WEBSITE:=https://github.com/ncmpcpp/ncmpcpp
### CHANGES:=https://github.com/ncmpcpp/ncmpcpp/releases

$(PKG)_BINARY:=$($(PKG)_DIR)/src/ncmpcpp
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/ncmpcpp

$(PKG)_DEPENDS_ON += libmpdclient
$(PKG)_DEPENDS_ON += ncursesw
$(PKG)_DEPENDS_ON += curl
$(PKG)_DEPENDS_ON += taglib

NCMPCPP_BOOST_VERSION:=1.87.0
NCMPCPP_BOOST_SOURCE:=ncmpcpp-boost_$(subst .,_,$(NCMPCPP_BOOST_VERSION)).tar.bz2
NCMPCPP_BOOST_SOURCE_DOWNLOAD_NAME:=boost_$(subst .,_,$(NCMPCPP_BOOST_VERSION)).tar.bz2
NCMPCPP_BOOST_HASH:=af57be25cb4c4f4b413ed692fe378affb4352ea50fbe294a11ef548f4d527d89
NCMPCPP_BOOST_SITE:=https://archives.boost.io/release/$(NCMPCPP_BOOST_VERSION)/source
NCMPCPP_BOOST_ROOT:=$(NCMPCPP_DIR)/.boost/boost_$(subst .,_,$(NCMPCPP_BOOST_VERSION))
NCMPCPP_BOOST_MARKER:=$(NCMPCPP_BOOST_ROOT)/.unpacked

$(PKG)_CONFIGURE_ENV += BOOST_LOCALE_LIBS=' '
$(PKG)_CONFIGURE_ENV += BOOST_LOCALE_LDFLAGS=' '
$(PKG)_CONFIGURE_ENV += boost_cv_lib_locale=yes
$(PKG)_CONFIGURE_ENV += boost_cv_lib_locale_LIBS=' '
$(PKG)_CONFIGURE_ENV += boost_cv_lib_locale_LDFLAGS=' '
$(PKG)_CONFIGURE_ENV += PKG_CONFIG_LIBDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig:$(TARGET_TOOLCHAIN_STAGING_DIR)/lib/pkgconfig"
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-shared
$(PKG)_CONFIGURE_OPTIONS += --with-taglib
$(PKG)_CONFIGURE_OPTIONS += --with-curl
$(PKG)_CONFIGURE_OPTIONS += --with-boost="$(abspath $(NCMPCPP_BOOST_ROOT))"
$(PKG)_CONFIGURE_OPTIONS += --enable-clock
$(PKG)_CONFIGURE_OPTIONS += --enable-outputs
$(PKG)_CONFIGURE_OPTIONS += --enable-visualizer
$(PKG)_CONFIGURE_OPTIONS += --disable-unicode
$(PKG)_CONFIGURE_OPTIONS += CXXFLAGS="-O2 -pipe -march=24kc -mno-dsp -Wno-deprecated -DBOOST_FILESYSTEM_DISABLE_STATX"

$(PKG)_CONFIGURE_PRE_CMDS += sed -i 's/^BOOST_LOCALE$$/dnl BOOST_LOCALE/' configure.ac;
$(PKG)_CONFIGURE_PRE_CMDS += autoreconf -fi;

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$(DL_DIR)/$(NCMPCPP_BOOST_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(NCMPCPP_BOOST_SOURCE) $(DL_DIR) $(NCMPCPP_BOOST_SOURCE_DOWNLOAD_NAME) $(NCMPCPP_BOOST_SITE) $(NCMPCPP_BOOST_HASH)

# Boost marker depends only on the downloaded archive, not on source .unpacked
# to avoid rebuilding boost on every recompile (source .unpacked timestamp changes).
# If you bump ncmpcpp version or need fresh boost, delete .boost/ manually.
$(NCMPCPP_BOOST_MARKER): $(DL_DIR)/$(NCMPCPP_BOOST_SOURCE)
	$(RM) -r $(NCMPCPP_DIR)/.boost
	mkdir -p $(NCMPCPP_DIR)/.boost
	$(call UNPACK_TARBALL,$<,$(NCMPCPP_DIR)/.boost)
	# Step 1: build b2 engine with host compiler (need to clear cross-env)
	cd $(NCMPCPP_BOOST_ROOT) && \
		unset MAKE CC CXX CFLAGS CXXFLAGS LDFLAGS LD_RUN_PATH PKG_CONFIG_PATH PKG_CONFIG_LIBDIR PKG_CONFIG_SYSROOT_DIR; \
		./bootstrap.sh --with-toolset=gcc
	# Step 2: configure cross-compilation and build boost libs
	cd $(NCMPCPP_BOOST_ROOT) && unset MAKE && \
		echo "using gcc : freetz : $(TARGET_CXX) ;" > tools/build/src/user-config.jam && \
		./b2 toolset=gcc-freetz --with-date_time --with-system --with-filesystem --with-thread --with-program_options --with-regex --with-atomic -sHAVE_ICU=0 link=static runtime-link=static variant=release threading=multi --layout=system "cxxflags=-DBOOST_FILESYSTEM_DISABLE_STATX" stage && \
		mkdir -p lib && cp stage/lib/*.a lib/
	# Step 3: create symlinks for all boost naming variants (tagged, versioned, etc)
	cd $(NCMPCPP_BOOST_ROOT)/lib && \
		for f in $$(ls libboost_*.a | grep -v -- '-'); do \
			base="$${f#lib}"; base="$${base%.a}"; \
			for suffix in "-d" "-mt" "-mt-d" "-mt-s" "-d-s" "-s" "-1_87" "-d-1_87" "-mt-1_87" "-mt-d-1_87" "-mt-s-1_87" "-d-s-1_87" "-s-1_87"; do \
				ln -sf "$$f" "lib$${base}$${suffix}.a" 2>/dev/null || true; \
				ln -sf "$$f" "lib$${base}-$${suffix}.a" 2>/dev/null || true; \
			done; \
		done
	@touch $@

$(PKG_CONFIGURED_CONFIGURE)

# Add boost headers as additional prerequisite for configure
$($(PKG)_DIR)/.configured: $(NCMPCPP_BOOST_MARKER)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(NCMPCPP_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(NCMPCPP_DIR) clean

$(pkg)-uninstall:
	$(RM) $(NCMPCPP_TARGET_BINARY)
	$(RM) $($(PKG)_DEST_DIR)/usr/share/ncmpcpp -rf

$(PKG_FINISH)
