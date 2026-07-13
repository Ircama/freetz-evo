$(call PKG_INIT_LIB, 1.1.1)
# Project version 1.1.1, library SO versions differ per sub-lib
$(PKG)_SOURCE:=libtheora-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=b6ae1ee2fa3d42ac489287d3ec34c5885730b1296f0801ae577a35193d3affbc
$(PKG)_SITE:=https://downloads.xiph.org/releases/theora
### WEBSITE:=https://www.theora.org/

# Three libraries: main (SO 0.3.10), decoder (SO 1.1.4), encoder (SO 1.1.2, stub if --disable-encode)
$(PKG)_LIBVERSIONS      := 0.3.10 1.1.4 1.1.2
$(PKG)_LIBNAMES_SHORT   := theora theoradec theoraenc
$(PKG)_LIBNAMES_LONG    := $(join $($(PKG)_LIBNAMES_SHORT:%=lib%.so.),$($(PKG)_LIBVERSIONS))
$(PKG)_LIBS_BUILD_DIR   := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_DIR)/lib/.libs/%)
$(PKG)_LIBS_STAGING_DIR := $($(PKG)_LIBNAMES_LONG:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%)
$(PKG)_LIBS_TARGET_DIR  := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_TARGET_DIR)/%)

$(PKG)_DEPENDS_ON += libogg libvorbis

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --disable-examples
$(PKG)_CONFIGURE_OPTIONS += --disable-encode
$(PKG)_CONFIGURE_OPTIONS += --disable-spec
$(PKG)_CONFIGURE_OPTIONS += --disable-doc

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIBS_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBTHEORA_DIR) all

$($(PKG)_LIBS_STAGING_DIR): $($(PKG)_LIBS_BUILD_DIR)
	$(SUBMAKE) -C $(LIBTHEORA_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_LIBS_TARGET_DIR): $($(PKG)_TARGET_DIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_LIBS_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_LIBS_TARGET_DIR)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBTHEORA_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libtheora* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/theora*

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libtheora.so* $($(PKG)_TARGET_DIR)/libtheoradec.so* $($(PKG)_TARGET_DIR)/libtheoraenc.so*

$(PKG_FINISH)
