$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(SHAIRPORT_SYNC_CGI_MAKE_DIR)/files/.language \
	$(SHAIRPORT_SYNC_CGI_MAKE_DIR)/files/root/etc/default.shairport-sync/shairport-sync.cfg \
	$(SHAIRPORT_SYNC_CGI_MAKE_DIR)/files/root/etc/default.shairport-sync/shairport-sync_conf \
	$(SHAIRPORT_SYNC_CGI_MAKE_DIR)/files/root/etc/init.d/rc.shairport-sync \
	$(SHAIRPORT_SYNC_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/shairport-sync.cgi \
	$(SHAIRPORT_SYNC_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/shairport-sync/status.cgi
$(PKG)_STAGING_TARGET := $(SHAIRPORT_SYNC_CGI_DEST_DIR)/usr/lib/cgi-bin/shairport-sync.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(SHAIRPORT_SYNC_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(SHAIRPORT_SYNC_CGI_MAKE_DIR)/files,$(SHAIRPORT_SYNC_CGI_TARGET_DIR))
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)