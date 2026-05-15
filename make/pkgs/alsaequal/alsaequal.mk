$(call PKG_INIT_BIN, 0.7.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=25a3da01fd471015ecefe679bcf157be47af307cc11ac5e5888157291eb8ce54
$(PKG)_SITE:=https://github.com/bassdr/alsaequal/archive/refs/tags
### WEBSITE:=https://github.com/bassdr/alsaequal
### MANPAGE:=https://github.com/bassdr/alsaequal#readme
### CHANGES:=https://github.com/bassdr/alsaequal/releases
### CVSREPO:=https://github.com/bassdr/alsaequal
### STEWARD:=Ircama
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/alsaequal/

$(PKG)_CATEGORY:=Audio

$(PKG)_DEPENDS_ON += alsa-lib

$(PKG)_MODULES := \
	libasound_module_pcm_equal.so \
	libasound_module_ctl_equal.so
$(PKG)_MODULES_BUILD_DIR := $($(PKG)_MODULES:%=$($(PKG)_DIR)/%)
$(PKG)_TARGET_INSTALL_MARKER := $($(PKG)_DEST_DIR)/.installed

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_MODULES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE1) -C $(ALSAEQUAL_DIR) \
		CC="$(TARGET_CC)" \
		LD="$(TARGET_CC)" \
		CFLAGS="$(TARGET_CFLAGS) -Wall -funroll-loops -ffast-math -fPIC -DPIC" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(abspath $(ALSAEQUAL_MAKE_DIR)/files/include)" \
		LDFLAGS="$(TARGET_LDFLAGS) -Wall -shared" \
		SND_PCM_LIBS="-lasound" \
		SND_CTL_LIBS="-lasound"

$($(PKG)_TARGET_INSTALL_MARKER): $($(PKG)_MODULES_BUILD_DIR)
	$(SUBMAKE1) -C $(ALSAEQUAL_DIR) \
		CC="$(TARGET_CC)" \
		LD="$(TARGET_CC)" \
		CFLAGS="$(TARGET_CFLAGS) -Wall -funroll-loops -ffast-math -fPIC -DPIC" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(abspath $(ALSAEQUAL_MAKE_DIR)/files/include)" \
		LDFLAGS="$(TARGET_LDFLAGS) -Wall -shared" \
		SND_PCM_LIBS="-lasound" \
		SND_CTL_LIBS="-lasound" \
		LIBDIR=lib \
		DESTDIR="$(abspath $(ALSAEQUAL_DEST_DIR))" \
		install
	$(TARGET_STRIP) $(ALSAEQUAL_DEST_DIR)/usr/lib/alsa-lib/libasound_module_pcm_equal.so 2>/dev/null || true
	$(TARGET_STRIP) $(ALSAEQUAL_DEST_DIR)/usr/lib/alsa-lib/libasound_module_ctl_equal.so 2>/dev/null || true
	touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_INSTALL_MARKER)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ALSAEQUAL_DIR) clean

$(pkg)-uninstall:
	$(RM) -f \
		$(ALSAEQUAL_DEST_DIR)/usr/lib/alsa-lib/libasound_module_pcm_equal.so \
		$(ALSAEQUAL_DEST_DIR)/usr/lib/alsa-lib/libasound_module_ctl_equal.so \
		$(ALSAEQUAL_TARGET_INSTALL_MARKER)

$(PKG_FINISH)