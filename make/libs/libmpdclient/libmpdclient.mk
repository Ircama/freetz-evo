$(call PKG_INIT_LIB, 2.22)
$(PKG)_LIB_VERSION:=$($(PKG)_VERSION)
$(PKG)_SOURCE:=libmpdclient-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=eac15b82b5ba5ed0648af580221eb74657394f7fe768e966d9e9ebb27435429f
$(PKG)_SITE:=https://www.musicpd.org/download/libmpdclient/2
### WEBSITE:=https://www.musicpd.org/libs/libmpdclient/
### MANPAGE:=https://www.musicpd.org/doc/libmpdclient/
### CHANGES:=https://github.com/MusicPlayerDaemon/libmpdclient/releases
### CVSREPO:=https://github.com/MusicPlayerDaemon/libmpdclient
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/libs/libmpdclient/

$(PKG)_CATEGORY_LIBS:=Multimedia
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmpdclient.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libmpdclient.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += meson-host

LIBMPDCLIENT_MESON_ENV := PATH="$(abspath $(TOOLS_DIR)/path):$(subst ",,$(TARGET_PATH))" $(FREETZ_LD_RUN_PATH) FREETZ_LIBRARY_DIR="$(FREETZ_LIBRARY_DIR)"

$(PKG)_CONFIGURE_ENV += PATH="$(abspath $(TOOLS_DIR)/path):$(subst ",,$(TARGET_PATH))"
$(PKG)_CONFIGURE_ENV += FREETZ_LIBRARY_DIR="$(FREETZ_LIBRARY_DIR)"

$(PKG)_CONFIGURE_OPTIONS += -D documentation=false
$(PKG)_CONFIGURE_OPTIONS += -D test=false
$(PKG)_CONFIGURE_OPTIONS += -D default_socket=/var/run/mpd/socket
$(PKG)_CONFIGURE_OPTIONS += -D default_host=localhost
$(PKG)_CONFIGURE_OPTIONS += -D default_port=6600

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_MESON)

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.configured
	cmd() { $(LIBMPDCLIENT_MESON_ENV) $(MESON) "$$@" $(SILENT) || { $(call ERROR,1,$(BUILD_FAIL_MSG)) } ; }; $(call _ECHO,building) cmd compile \
		-C $(LIBMPDCLIENT_DIR)/builddir/
	cmd() { $(LIBMPDCLIENT_MESON_ENV) $(MESON) "$$@" $(SILENT) || { $(call ERROR,1,$(BUILD_FAIL_MSG)) } ; }; $(call _ECHO,building) cmd install \
		--destdir "$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		-C $(LIBMPDCLIENT_DIR)/builddir/
	# Ensure libmpdclient.pc is staged (meson install may skip it in some cases)
	install -D -m 644 $(LIBMPDCLIENT_DIR)/builddir/meson-private/libmpdclient.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libmpdclient.pc
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/doc/libmpdclient

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBNINJA) -C $(LIBMPDCLIENT_DIR)/builddir/ clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/mpd \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmpdclient.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libmpdclient.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/doc/libmpdclient

$(pkg)-uninstall:
	$(RM) $(LIBMPDCLIENT_TARGET_DIR)/libmpdclient.so*

$(PKG_FINISH)