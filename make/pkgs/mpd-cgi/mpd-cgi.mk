$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(MPD_CGI_MAKE_DIR)/files/.language \
	$(MPD_CGI_MAKE_DIR)/files/root/etc/default.mpd/mpd.cfg \
	$(MPD_CGI_MAKE_DIR)/files/root/etc/default.mpd/mpd_conf \
	$(MPD_CGI_MAKE_DIR)/files/root/etc/init.d/rc.mpd \
	$(MPD_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/mpd.cgi \
	$(MPD_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/mpd/status.cgi
$(PKG)_STAGING_TARGET := $(MPD_CGI_DEST_DIR)/usr/lib/cgi-bin/mpd.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(MPD_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(MPD_CGI_MAKE_DIR)/files,$(MPD_CGI_TARGET_DIR))
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)