$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(MPD_MPC_CGI_MAKE_DIR)/files/.language \
	$(MPD_MPC_CGI_MAKE_DIR)/files/root/etc/default.mpd-mpc/mpd-mpc.cfg \
	$(MPD_MPC_CGI_MAKE_DIR)/files/root/etc/init.d/rc.mpd-mpc \
	$(MPD_MPC_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/mpd-mpc.cgi \
	$(MPD_MPC_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/mpd-mpc/status.cgi
$(PKG)_STAGING_TARGET := $(MPD_MPC_CGI_DEST_DIR)/usr/lib/cgi-bin/mpd-mpc.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(MPD_MPC_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(MPD_MPC_CGI_MAKE_DIR)/files,$(MPD_MPC_CGI_TARGET_DIR))
	chmod 755 \
		$(MPD_MPC_CGI_DEST_DIR)/etc/init.d/rc.mpd-mpc \
		$(MPD_MPC_CGI_DEST_DIR)/usr/lib/cgi-bin/mpd-mpc.cgi \
		$(MPD_MPC_CGI_DEST_DIR)/usr/lib/cgi-bin/mpd-mpc/status.cgi
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)
