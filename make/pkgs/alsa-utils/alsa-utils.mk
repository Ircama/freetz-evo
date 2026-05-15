$(call PKG_INIT_BIN, 1.2.13)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=1702a6b1cdf9ba3e996ecbc1ddcf9171e6808f5961d503d0f27e80ee162f1daa
$(PKG)_SITE:=https://www.alsa-project.org/files/pub/utils
### WEBSITE:=https://www.alsa-project.org/wiki/Main_Page
### CHANGES:=https://www.alsa-project.org/wiki/Detailed_changes_v1.2.12_v1.2.13

$(PKG)_CATEGORY:=Audio

$(PKG)_TARGET_INSTALL_MARKER:=$($(PKG)_DEST_DIR)/.installed

$(PKG)_DEPENDS_ON += alsa-lib

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

# alsamixer needs the ncurses UI stack, which this lean build avoids.
$(PKG)_CONFIGURE_OPTIONS += --disable-alsamixer
$(PKG)_CONFIGURE_OPTIONS += --disable-alsaconf
$(PKG)_CONFIGURE_OPTIONS += --disable-alsaloop
$(PKG)_CONFIGURE_OPTIONS += --disable-bat
$(PKG)_CONFIGURE_OPTIONS += --disable-nhlt
$(PKG)_CONFIGURE_OPTIONS += --disable-xmlto
$(PKG)_CONFIGURE_OPTIONS += --disable-rst2man
$(PKG)_CONFIGURE_OPTIONS += --disable-nls

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_TARGET_INSTALL_MARKER): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(ALSA_UTILS_DIR)
	$(SUBMAKE) -C $(ALSA_UTILS_DIR) DESTDIR="$(abspath $(ALSA_UTILS_DEST_DIR))" install
	$(RM) -r \
		$(ALSA_UTILS_DEST_DIR)/usr/share/doc \
		$(ALSA_UTILS_DEST_DIR)/usr/share/info \
		$(ALSA_UTILS_DEST_DIR)/usr/share/locale \
		$(ALSA_UTILS_DEST_DIR)/usr/share/man
	@if [ -d "$(ALSA_UTILS_DEST_DIR)/usr/bin" ]; then \
		find "$(ALSA_UTILS_DEST_DIR)/usr/bin" -type f -perm -0100 -exec $(TARGET_STRIP) {} + 2>/dev/null || true; \
	fi
	@if [ -d "$(ALSA_UTILS_DEST_DIR)/usr/sbin" ]; then \
		find "$(ALSA_UTILS_DEST_DIR)/usr/sbin" -type f -perm -0100 -exec $(TARGET_STRIP) {} + 2>/dev/null || true; \
	fi
	touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_INSTALL_MARKER)


$(pkg)-clean:
	-$(SUBMAKE) -C $(ALSA_UTILS_DIR) clean

$(pkg)-uninstall:
	$(RM) -r \
		$(ALSA_UTILS_DEST_DIR)/usr/bin \
		$(ALSA_UTILS_DEST_DIR)/usr/sbin \
		$(ALSA_UTILS_DEST_DIR)/usr/share/alsa \
		$(ALSA_UTILS_TARGET_INSTALL_MARKER)

$(PKG_FINISH)