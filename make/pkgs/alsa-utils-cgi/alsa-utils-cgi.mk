$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(ALSA_UTILS_CGI_MAKE_DIR)/files/.language \
	$(ALSA_UTILS_CGI_MAKE_DIR)/files/root/etc/default.alsa-utils/alsa-utils.cfg \
	$(ALSA_UTILS_CGI_MAKE_DIR)/files/root/etc/init.d/rc.alsa-utils \
	$(ALSA_UTILS_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/alsa-utils.cgi \
	$(ALSA_UTILS_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/alsa-utils/status.cgi
$(PKG)_STAGING_TARGET := $(ALSA_UTILS_CGI_DEST_DIR)/usr/lib/cgi-bin/alsa-utils.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(ALSA_UTILS_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(ALSA_UTILS_CGI_MAKE_DIR)/files,$(ALSA_UTILS_CGI_TARGET_DIR))
	chmod 755 \
		$(ALSA_UTILS_CGI_DEST_DIR)/etc/init.d/rc.alsa-utils \
		$(ALSA_UTILS_CGI_DEST_DIR)/usr/lib/cgi-bin/alsa-utils.cgi \
		$(ALSA_UTILS_CGI_DEST_DIR)/usr/lib/cgi-bin/alsa-utils/status.cgi
	touch $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)