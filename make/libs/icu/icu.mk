$(call PKG_INIT_LIB, 76.1)
$(PKG)_LIB_VERSION:=76.1
$(PKG)_SOURCE:=icu4c-$(subst .,_,$($(PKG)_VERSION))-src.tgz
$(PKG)_HASH:=dfacb46bfe4747410472ce3e1144bf28a102feeaa4e3875bac9b4c6cf30f4f3e
$(PKG)_SITE:=https://github.com/unicode-org/icu/releases/download/release-$(subst .,-,$($(PKG)_VERSION))
### WEBSITE:=https://icu.unicode.org/
### CHANGES:=https://github.com/unicode-org/icu/releases
### CVSREPO:=https://github.com/unicode-org/icu

# ICU tarball structure: icu/source/{configure,...}. After strip-components=1
# the source/ contents land inside $(PKG)_DIR/source/
# ICU produces multiple shared libraries; define a list for automated install.
$(PKG)_ICU_LIBS := libicudata libicui18n libicuio libicuuc

$(PKG)_BINARY:=$($(PKG)_DIR)/source/lib/libicui18n.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libicui18n.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARIES := $($(PKG)_ICU_LIBS:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%.so.$($(PKG)_LIB_VERSION))
$(PKG)_TARGET_BINARIES  := $($(PKG)_ICU_LIBS:%=$($(PKG)_TARGET_DIR)/%.so.$($(PKG)_LIB_VERSION))

$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-samples
$(PKG)_CONFIGURE_OPTIONS += --disable-tests
$(PKG)_CONFIGURE_OPTIONS += --disable-layout
# $(PKG)_CONFIGURE_OPTIONS += --disable-renaming  # removed: gerbera expects icu_76:: namespace (default with renaming)
$(PKG)_CONFIGURE_OPTIONS += --with-data-packaging=static
# uClibc lacks std::filesystem, disable C++17 filesystem usage
$(PKG)_CONFIGURE_OPTIONS += --disable-icu-config-path

# ICU requires a native (host) build first when cross-compiling.
# We build minimal ICU host tools inside a subdirectory.
$(PKG)_HOST_BUILD_DIR:=$(ICU_DIR)/host-build

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	abs_icu_src="$(FREETZ_BASE_DIR)/$(ICU_DIR)/source" && \
	mkdir -p $(ICU_HOST_BUILD_DIR) && \
	cd $(ICU_HOST_BUILD_DIR) && \
		CC=gcc CXX=g++ "$$abs_icu_src/configure" \
		--enable-tools --disable-tests --disable-samples \
		--with-data-packaging=static && \
		$(MAKE1) && \
	cd "$(FREETZ_BASE_DIR)/$(ICU_DIR)/source" && \
		$(TARGET_CONFIGURE_ENV) PYTHON=/usr/bin/python3 \
		./configure \
		--host=$(GNU_TARGET_NAME) \
		--build=$(GNU_HOST_NAME) \
		--prefix="/usr" \
		--with-cross-build=$(FREETZ_BASE_DIR)/$(ICU_HOST_BUILD_DIR) \
		$(ICU_CONFIGURE_OPTIONS)
	@touch $@

# Build all ICU libraries at once
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(ICU_DIR)/source

# Install all ICU libraries to staging
$($(PKG)_STAGING_BINARIES): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(ICU_DIR)/source \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install

# Copy each ICU library from staging to target directory
$($(PKG)_TARGET_BINARIES): $($(PKG)_TARGET_DIR)/%.so.$($(PKG)_LIB_VERSION): $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%.so.$($(PKG)_LIB_VERSION)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARIES)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARIES)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ICU_DIR)/source clean 2>/dev/null || true
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/unicode \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libicu* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/icu*.pc

$(pkg)-uninstall:
	$(RM) $(ICU_TARGET_DIR)/libicu*.so*

$(PKG_FINISH)
