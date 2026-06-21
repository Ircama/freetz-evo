$(call PKG_INIT_LIB, 1.2.13)
$(PKG)_LIB_VERSION:=2.0.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=8c4ff37553cbe89618e187e4c779f71a9bb2a8b27b91f87ed40987cc9233d8f6
$(PKG)_SITE:=https://www.alsa-project.org/files/pub/lib
### WEBSITE:=https://www.alsa-project.org/wiki/Main_Page
### CHANGES:=https://www.alsa-project.org/wiki/Detailed_changes_v1.2.12_v1.2.13

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libasound.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libasound.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libasound.so.$($(PKG)_LIB_VERSION)

$(PKG)_DATA_MARKER_FILE := alsa.conf
$(PKG)_DATA_DIR := /usr/share/alsa
$(PKG)_DATA_STAGING_DIR := $(TARGET_TOOLCHAIN_STAGING_DIR)$($(PKG)_DATA_DIR)
$(PKG)_DATA_TARGET_DIR := $($(PKG)_DEST_DIR)$($(PKG)_DATA_DIR)

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --disable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-python
$(PKG)_CONFIGURE_OPTIONS += --disable-topology
$(PKG)_CONFIGURE_OPTIONS += --disable-ucm
$(PKG)_CONFIGURE_OPTIONS += --with-versioned=no

$(PKG)_DEPENDS_ON += speex

$(PKG)_DATA_CONFIG_FILE := $($(PKG)_DATA_STAGING_DIR)/$($(PKG)_DATA_MARKER_FILE)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(ALSA_LIB_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(ALSA_LIB_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	# Ensure alsa.pc is installed (recursive install from top-level may skip utils/)
	$(SUBMAKE) -C $(ALSA_LIB_DIR)/utils \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install-pkgconfigDATA 2>/dev/null || true
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libasound.la \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/alsa.pc
	sed -i -e 's|^defaults\.pcm\.ipc_gid audio$$|defaults.pcm.ipc_gid root|' $(ALSA_LIB_DATA_CONFIG_FILE)
	# Set speexrate as the default rate converter for better audio quality
	# (requires libspeex which is auto-selected by alsa-lib)
	if grep -q '^defaults.pcm.rate_converter' $(ALSA_LIB_DATA_CONFIG_FILE); then \
		sed -i 's|^defaults.pcm.rate_converter.*|defaults.pcm.rate_converter "speexrate"|' $(ALSA_LIB_DATA_CONFIG_FILE); \
	else \
		sed -i '/^defaults.pcm.ipc_gid/a\defaults.pcm.rate_converter "speexrate"' $(ALSA_LIB_DATA_CONFIG_FILE); \
	fi

$($(PKG)_DATA_STAGING_DIR)/$($(PKG)_DATA_MARKER_FILE): $($(PKG)_STAGING_BINARY)
	[ -f "$@" ]

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

define $(PKG)_INSTALL_DIR_RULE
$(1): $(2)
	$$(RM) -r $$(dir $$@); \
	mkdir -p $$(dir $$@); \
	cp -a $$(dir $$<)/* $$(dir $$@); \
	touch $$@
endef

$(eval $(call $(PKG)_INSTALL_DIR_RULE,$($(PKG)_DATA_TARGET_DIR)/$($(PKG)_DATA_MARKER_FILE),$($(PKG)_DATA_STAGING_DIR)/$($(PKG)_DATA_MARKER_FILE)))

$(pkg): $($(PKG)_STAGING_BINARY) $($(PKG)_DATA_STAGING_DIR)/$($(PKG)_DATA_MARKER_FILE)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_DATA_TARGET_DIR)/$($(PKG)_DATA_MARKER_FILE)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ALSA_LIB_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/alsa \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libasound* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/alsa.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/aclocal/alsa.m4 \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/alsa

$(pkg)-uninstall:
	$(RM) -r \
		$(ALSA_LIB_TARGET_DIR)/libasound*.so* \
		$(ALSA_LIB_DATA_TARGET_DIR)

$(PKG_FINISH)