$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(ALSAEQUAL_CGI_MAKE_DIR)/files/.language \
	$(ALSAEQUAL_CGI_MAKE_DIR)/files/root/etc/default.alsaequal/alsaequal.cfg \
	$(ALSAEQUAL_CGI_MAKE_DIR)/files/root/etc/default.alsaequal/alsaequal.save \
	$(ALSAEQUAL_CGI_MAKE_DIR)/files/root/etc/default.alsaequal/alsaequal_conf \
	$(ALSAEQUAL_CGI_MAKE_DIR)/files/root/etc/init.d/rc.alsaequal \
	$(ALSAEQUAL_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/alsaequal.cgi \
	$(ALSAEQUAL_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/alsaequal/status.cgi
$(PKG)_STAGING_TARGET := $(ALSAEQUAL_CGI_DEST_DIR)/usr/lib/cgi-bin/alsaequal.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(ALSAEQUAL_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(ALSAEQUAL_CGI_MAKE_DIR)/files,$(ALSAEQUAL_CGI_TARGET_DIR))
	chmod 755 \
		$(ALSAEQUAL_CGI_DEST_DIR)/etc/default.alsaequal/alsaequal.save \
		$(ALSAEQUAL_CGI_DEST_DIR)/etc/default.alsaequal/alsaequal_conf \
		$(ALSAEQUAL_CGI_DEST_DIR)/etc/init.d/rc.alsaequal \
		$(ALSAEQUAL_CGI_DEST_DIR)/usr/lib/cgi-bin/alsaequal.cgi \
		$(ALSAEQUAL_CGI_DEST_DIR)/usr/lib/cgi-bin/alsaequal/status.cgi
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)