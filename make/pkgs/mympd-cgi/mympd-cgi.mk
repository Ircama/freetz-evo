$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(MYMPD_CGI_MAKE_DIR)/files/.language \
	$(MYMPD_CGI_MAKE_DIR)/files/root/etc/default.mympd/mympd.cfg \
	$(MYMPD_CGI_MAKE_DIR)/files/root/etc/init.d/rc.mympd \
	$(MYMPD_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/mympd.cgi \
	$(MYMPD_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/mympd/status.cgi
$(PKG)_STAGING_TARGET := $(MYMPD_CGI_DEST_DIR)/usr/lib/cgi-bin/mympd.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(MYMPD_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(MYMPD_CGI_MAKE_DIR)/files,$(MYMPD_CGI_TARGET_DIR))
	chmod 755 \
		$(MYMPD_CGI_DEST_DIR)/etc/init.d/rc.mympd \
		$(MYMPD_CGI_DEST_DIR)/usr/lib/cgi-bin/mympd.cgi \
		$(MYMPD_CGI_DEST_DIR)/usr/lib/cgi-bin/mympd/status.cgi

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)