$(call PKG_INIT_BIN, 0.35, mpd-mpc, MPD_MPC)
$(PKG)_SOURCE:=mpc-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=382959c3bfa2765b5346232438650491b822a16607ff5699178aa1386e3878d4
$(PKG)_SITE:=https://www.musicpd.org/download/mpc/0
$(PKG)_DIR:=$(SOURCE_DIR)/mpc-$($(PKG)_VERSION)
### WEBSITE:=https://www.musicpd.org/clients/mpc/
### MANPAGE:=https://www.musicpd.org/doc/mpc/html/
### CHANGES:=https://github.com/MusicPlayerDaemon/mpc/releases
### CVSREPO:=https://github.com/MusicPlayerDaemon/mpc
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/mpd-mpc/

$(PKG)_CATEGORY:=Audio

$(PKG)_BINARY:=$($(PKG)_DIR)/builddir/mpc
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/mpc

$(PKG)_DEPENDS_ON += meson-host libmpdclient

MPD_MPC_MESON_ENV := PATH="$(abspath $(TOOLS_DIR)/path):$(subst ",,$(TARGET_PATH))" $(FREETZ_LD_RUN_PATH) FREETZ_LIBRARY_DIR="$(FREETZ_LIBRARY_DIR)"

$(PKG)_CONFIGURE_ENV += PATH="$(abspath $(TOOLS_DIR)/path):$(subst ",,$(TARGET_PATH))"
$(PKG)_CONFIGURE_ENV += FREETZ_LIBRARY_DIR="$(FREETZ_LIBRARY_DIR)"

$(PKG)_CONFIGURE_OPTIONS += --wrap-mode=nofallback
$(PKG)_CONFIGURE_OPTIONS += -D documentation=disabled
$(PKG)_CONFIGURE_OPTIONS += -D test=false

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_MESON)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	cmd() { $(MPD_MPC_MESON_ENV) $(MESON) "$$@" $(SILENT) || { $(call ERROR,1,$(BUILD_FAIL_MSG)) } ; }; $(call _ECHO,building) cmd compile \
		-C $(MPD_MPC_DIR)/builddir/

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBNINJA) -C $(MPD_MPC_DIR)/builddir/ clean
	$(RM) $(MPD_MPC_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(MPD_MPC_TARGET_BINARY)

$(PKG_FINISH)