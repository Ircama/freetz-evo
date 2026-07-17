$(call PKG_INIT_BIN, 1.0)
$(PKG)_CATEGORY:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(GERBERA_CGI_MAKE_DIR)/files/.language \
	$(GERBERA_CGI_MAKE_DIR)/files/root/etc/init.d/rc.gerbera \
	$(GERBERA_CGI_MAKE_DIR)/files/root/etc/default.gerbera/gerbera.cfg \
	$(GERBERA_CGI_MAKE_DIR)/files/root/etc/default.gerbera/gerbera.save \
	$(GERBERA_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/gerbera.cgi \
	$(GERBERA_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/gerbera/status.cgi
$(PKG)_STAGING_TARGET := $(GERBERA_CGI_DEST_DIR)/usr/lib/cgi-bin/gerbera.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(GERBERA_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(GERBERA_CGI_MAKE_DIR)/files,$(GERBERA_CGI_TARGET_DIR))
	chmod 755 \
		$(GERBERA_CGI_DEST_DIR)/etc/init.d/rc.gerbera \
		$(GERBERA_CGI_DEST_DIR)/usr/lib/cgi-bin/gerbera.cgi \
		$(GERBERA_CGI_DEST_DIR)/usr/lib/cgi-bin/gerbera/status.cgi
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)
