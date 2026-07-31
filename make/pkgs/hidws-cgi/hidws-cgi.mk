$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(HIDWS_CGI_MAKE_DIR)/files/.language \
	$(HIDWS_CGI_MAKE_DIR)/files/root/etc/default.hidws/hidws.cfg \
	$(HIDWS_CGI_MAKE_DIR)/files/root/etc/default.hidws/hidws.save \
	$(HIDWS_CGI_MAKE_DIR)/files/root/etc/init.d/rc.hidws \
	$(HIDWS_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/hidws.cgi
$(PKG)_STAGING_TARGET := $(HIDWS_CGI_DEST_DIR)/usr/lib/cgi-bin/hidws.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(HIDWS_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(HIDWS_CGI_MAKE_DIR)/files,$(HIDWS_CGI_TARGET_DIR))
	chmod 755 \
		$(HIDWS_CGI_DEST_DIR)/etc/default.hidws/hidws.save \
		$(HIDWS_CGI_DEST_DIR)/etc/init.d/rc.hidws \
		$(HIDWS_CGI_DEST_DIR)/usr/lib/cgi-bin/hidws.cgi
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)
