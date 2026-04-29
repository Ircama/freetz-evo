$(call PKG_INIT_BIN, 0.1)
### STEWARD:=Ircama
$(PKG)_BINARY:=$($(PKG)_DIR)/freetz_proxy
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/www/cgi-bin/freetz_proxy
# Symlink in the AVM "all" OEM cgi-bin so the web server can find the CGI
# without depending on fwmod's symlink-creation step.
$(PKG)_TARGET_SYMLINK:=$($(PKG)_DEST_DIR)/usr/www/all/cgi-bin/freetz_proxy

$(PKG_LOCALSOURCE_PACKAGE)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(FREETZ_PROXY_DIR) \
		CC="$(TARGET_CC)" \
		CFLAGS="$(TARGET_CFLAGS)" \
		LDFLAGS="-static"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_TARGET_SYMLINK): $($(PKG)_TARGET_BINARY)
	mkdir -p $(dir $@)
	ln -sf ../../cgi-bin/freetz_proxy $@

# Fixed variable names: captured at parse time so recipes expand correctly
# at execution time (after $(PKG) has been overwritten by later packages).
FREETZ_PROXY_DEST          := $($(PKG)_DEST_DIR)
FREETZ_PROXY_TARGET_BINARY := $($(PKG)_DEST_DIR)/usr/www/cgi-bin/freetz_proxy
FREETZ_PROXY_TARGET_SYMLINK:= $($(PKG)_DEST_DIR)/usr/www/all/cgi-bin/freetz_proxy
FREETZ_PROXY_RC            := $($(PKG)_DEST_DIR)/etc/init.d/rc.freetz-proxy
FREETZ_PROXY_CGI           := $($(PKG)_DEST_DIR)/usr/lib/cgi-bin/freetz-proxy.cgi
FREETZ_PROXY_CFG           := $($(PKG)_DEST_DIR)/etc/default.freetz-proxy/freetz-proxy-services.cfg
FREETZ_PROXY_DEF           := $($(PKG)_DEST_DIR)/etc/default.freetz-proxy/freetz-proxy-cfg.def
FREETZ_PROXY_FILES_DIR     := $($(PKG)_MAKE_DIR)/files/root

$(FREETZ_PROXY_RC): $(FREETZ_PROXY_FILES_DIR)/etc/init.d/rc.freetz-proxy
	$(INSTALL_FILE)
	chmod 755 $@

$(FREETZ_PROXY_CGI): $(FREETZ_PROXY_FILES_DIR)/usr/lib/cgi-bin/freetz-proxy.cgi
	$(INSTALL_FILE)
	chmod 755 $@

$(FREETZ_PROXY_CFG): $(FREETZ_PROXY_FILES_DIR)/etc/default.freetz-proxy/freetz-proxy-services.cfg
	$(INSTALL_FILE)

$(FREETZ_PROXY_DEF): $(FREETZ_PROXY_FILES_DIR)/etc/default.freetz-proxy/freetz-proxy-cfg.def
	$(INSTALL_FILE)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_TARGET_SYMLINK) \
	$(FREETZ_PROXY_RC) $(FREETZ_PROXY_CGI) $(FREETZ_PROXY_CFG) $(FREETZ_PROXY_DEF)

$(pkg)-clean:
	-$(SUBMAKE) -C $(FREETZ_PROXY_DIR) clean

$(pkg)-uninstall:
	$(RM) $(FREETZ_PROXY_TARGET_BINARY)
	$(RM) $(FREETZ_PROXY_TARGET_SYMLINK)
	$(RM) $(FREETZ_PROXY_RC)
	$(RM) $(FREETZ_PROXY_CGI)
	$(RM) -r $(FREETZ_PROXY_DEST)/etc/default.freetz-proxy

$(PKG_FINISH)
