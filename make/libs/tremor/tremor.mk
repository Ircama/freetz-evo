$(call PKG_INIT_LIB, master)
# Project version 1.2.1, library SO version (1-0).0.3 = 1.0.3
$(PKG)_LIB_VERSION:=1.0.3
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=6eceff4526bd717c6956b3d49459e13b4cfcfe35781cf09a271790e4ace7315f
$(PKG)_SITE:=https://gitlab.xiph.org/xiph/tremor/-/archive/master
### WEBSITE:=https://wiki.xiph.org/Tremor

$(PKG)_BINARY:=$($(PKG)_DIR)/.libs/libvorbisidec.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libvorbisidec.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libvorbisidec.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += libogg

# No configure script in GitLab archive, need autoreconf.
# Patch configure.ac first to remove XIPH_PATH_OGG (macro not available on host)
$(PKG)_CONFIGURE_PRE_CMDS += $(SED) -i 's/XIPH_PATH_OGG(, AC_MSG_ERROR(must have Ogg installed!))/AC_MSG_ERROR([must have Ogg installed!])/' \
		configure.ac 2>/dev/null || true; \
	autoreconf -fi;

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TREMOR_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(TREMOR_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(TREMOR_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libvorbisidec.so*

$(PKG_FINISH)
