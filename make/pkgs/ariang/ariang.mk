$(call PKG_INIT_BIN, 1.3.13)
$(PKG)_SOURCE:=AriaNg-$($(PKG)_VERSION).zip
$(PKG)_HASH:=8ad64e6e8e6639d2d8125f6fae2110c1f4015cec8fe003aa563d2b372f889297
$(PKG)_SITE:=https://github.com/mayswind/AriaNg/releases/download/$($(PKG)_VERSION)
### WEBSITE:=https://github.com/mayswind/AriaNg
### MANPAGE:=https://github.com/mayswind/AriaNg/blob/master/README.md
### CHANGES:=https://github.com/mayswind/AriaNg/releases
### CVSREPO:=https://github.com/mayswind/AriaNg.git
### SUPPORT:=Ircama

# AriaNg is a web frontend for aria2, static files only (no compilation needed)
$(PKG)_DEPENDS_ON += aria2

# Shorthand variables for recipe expansion
ARIANG_DIR:=$($(PKG)_DIR)
ARIANG_DEST_DIR:=$($(PKG)_DEST_DIR)
ARIANG_SOURCE:=$($(PKG)_SOURCE)
ARIANG_MAKE_DIR:=$($(PKG)_MAKE_DIR)

# Extract - AriaNg is pure HTML/CSS/JS (no build needed)
$(PKG_SOURCE_DOWNLOAD)

# Custom unpacking: AriaNg zip doesn't have subdirectory, extract directly
$($(PKG)_DIR)/.unpacked: $($(PKG)_SOURCE_DOWNLOAD_TIMESTAMP)
	@echo "preparing ... "
	mkdir -p $(ARIANG_DIR)
	tools/unzip $(DL_DIR)/$(ARIANG_SOURCE) -d $(ARIANG_DIR)
	touch $@

$(PKG_CONFIGURED_NOP)

# Build target (no actual compilation, just marker)
$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	@echo "AriaNg is a static web frontend, installing to webcfg directory..."
	mkdir -p $(ARIANG_DEST_DIR)/usr/mww/ariang
	cp -r $(ARIANG_DIR)/* $(ARIANG_DEST_DIR)/usr/mww/ariang/
	# Copy Freetz EVO SSO PHP gateway
	cp $(ARIANG_MAKE_DIR)/files/root/usr/mww/ariang/ariang_auth.php \
		$(ARIANG_DEST_DIR)/usr/mww/ariang/ariang_auth.php
	# Inject Freetz EVO SSO preflight into AriaNg index.html
	python3 $(ARIANG_MAKE_DIR)/files/inject_sso.py \
		$(ARIANG_MAKE_DIR)/files/ariang_sso_snippet.html \
		$(ARIANG_DEST_DIR)/usr/mww/ariang/index.html
	touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.compiled

$(pkg)-clean:
	-[ -d $(ARIANG_DIR) ] && rm -rf $(ARIANG_DIR) || true

$(pkg)-distclean:
	-[ -d $(ARIANG_DIR) ] && rm -rf $(ARIANG_DIR) || true

$(pkg)-uninstall:
	$(RM) -r $(ARIANG_DEST_DIR)/usr/mww/ariang

$(PKG_FINISH)

