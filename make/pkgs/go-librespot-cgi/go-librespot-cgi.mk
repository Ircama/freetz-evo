$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY:=Web interfaces

$(PKG)_STAGING_SOURCES := \
	$(GO_LIBRESPOT_CGI_MAKE_DIR)/files/.language \
	$(GO_LIBRESPOT_CGI_MAKE_DIR)/files/root/etc/default.go-librespot/go-librespot.cfg \
	$(GO_LIBRESPOT_CGI_MAKE_DIR)/files/root/etc/default.go-librespot/go-librespot_conf \
	$(GO_LIBRESPOT_CGI_MAKE_DIR)/files/root/etc/init.d/rc.go-librespot \
	$(GO_LIBRESPOT_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/go-librespot.cgi \
	$(GO_LIBRESPOT_CGI_MAKE_DIR)/files/root/usr/lib/cgi-bin/go-librespot/status.cgi
$(PKG)_STAGING_TARGET := $(GO_LIBRESPOT_CGI_DEST_DIR)/usr/lib/cgi-bin/go-librespot.cgi

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(GO_LIBRESPOT_CGI_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(GO_LIBRESPOT_CGI_MAKE_DIR)/files,$(GO_LIBRESPOT_CGI_TARGET_DIR))

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_STAGING_TARGET)

$(pkg)-clean:

$(PKG_FINISH)