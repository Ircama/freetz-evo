$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(SNAPCAST_CGI_MAKE_DIR)/files/.language \
	$(SNAPCAST_CGI_MAKE_DIR)/files/root/etc/default.snapcast/snapcast.cfg \
	$(SNAPCAST_CGI_MAKE_DIR)/files/root/etc/default.snapcast/snapserver_conf \
	$(SNAPCAST_CGI_MAKE_DIR)/files/root/etc/init.d/rc.snapcast \
	$(SNAPCAST_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/snapcast.cgi \
	$(SNAPCAST_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/snapcast/status.cgi
$(PKG)_STAGING_TARGET := $(SNAPCAST_CGI_DEST_DIR)/usr/lib/cgi-bin/snapcast.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(SNAPCAST_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(SNAPCAST_CGI_MAKE_DIR)/files,$(SNAPCAST_CGI_TARGET_DIR))
	chmod 755 \
		$(SNAPCAST_CGI_DEST_DIR)/etc/default.snapcast/snapserver_conf \
		$(SNAPCAST_CGI_DEST_DIR)/etc/init.d/rc.snapcast \
		$(SNAPCAST_CGI_DEST_DIR)/usr/lib/cgi-bin/snapcast.cgi \
		$(SNAPCAST_CGI_DEST_DIR)/usr/lib/cgi-bin/snapcast/status.cgi
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)