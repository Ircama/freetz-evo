$(call PKG_INIT_BIN, 5.3.1)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=338d89c7842381b350e359f63d6595aa36d2472b22d8b6f02294d6ddcfd9ecb1
$(PKG)_SITE:=https://github.com/Novik/ruTorrent/archive/refs/tags
### WEBSITE:=https://github.com/Novik/ruTorrent
### MANPAGE:=https://github.com/Novik/ruTorrent/wiki
### CHANGES:=https://github.com/Novik/ruTorrent/releases
### CVSREPO:=https://github.com/Novik/ruTorrent
### SUPPORT:=Ircama

# ruTorrent unpacked directory
RUTORRENT_DIR:=$(SOURCE_DIR)/ruTorrent-$($(PKG)_VERSION)

# ruTorrent 3rd Party Plugins
# autodl-irssi plugin
AUTODL_RUTORRENT_VERSION:=2.3.0
AUTODL_RUTORRENT_SOURCE:=autodl-rutorrent-v$(AUTODL_RUTORRENT_VERSION).tar.gz
AUTODL_RUTORRENT_HASH:=42dbbc9061deb78f1a1bdae6b9ae5800dd05d8d3fb6ee6052a54127d6bf8b1c3
AUTODL_RUTORRENT_SITE:=https://github.com/autodl-community/autodl-rutorrent/archive/refs/tags
AUTODL_RUTORRENT_DIR:=$(SOURCE_DIR)/autodl-rutorrent-$(AUTODL_RUTORRENT_VERSION)

# rutorrentMobile plugin
PLUGIN_MOBILE_VERSION:=master
PLUGIN_MOBILE_SOURCE:=xombiemp-rutorrentMobile-$(PLUGIN_MOBILE_VERSION).tar.gz
PLUGIN_MOBILE_HASH:=b86b7c6df8d2b6f937f7fee7cd941e528f7e9e38eb4fe865d0246ffafc371d3a
PLUGIN_MOBILE_SITE:=https://github.com/xombiemp/rutorrentMobile/archive/refs/heads
PLUGIN_MOBILE_DIR:=$(SOURCE_DIR)/rutorrentMobile-$(PLUGIN_MOBILE_VERSION)

# nelu thirdparty plugins (filemanager, fileshare, fileupload, chat, nfo, hostname)
PLUGIN_NELU_VERSION:=master
PLUGIN_NELU_SOURCE:=nelu-rutorrent-thirdparty-$(PLUGIN_NELU_VERSION).tar.gz
PLUGIN_NELU_HASH:=17e8305e8b90f672b065f8f6e53fae33074f3d9230a090c05f65dc7b0f162602
PLUGIN_NELU_SITE:=https://github.com/nelu/rutorrent-thirdparty-plugins/archive/refs/heads
PLUGIN_NELU_DIR:=$(SOURCE_DIR)/rutorrent-thirdparty-plugins-$(PLUGIN_NELU_VERSION)

# filemanager plugin
PLUGIN_FILEMANAGER_VERSION:=v1.5.1
PLUGIN_FILEMANAGER_SOURCE:=nelu-rutorrent-filemanager-$(PLUGIN_FILEMANAGER_VERSION).tar.gz
PLUGIN_FILEMANAGER_HASH:=f90d4fa2f73136402fc0865c468e89b9bcd4b3995ec6b298e65d03cf28f644bf
PLUGIN_FILEMANAGER_SITE:=https://github.com/nelu/rutorrent-filemanager/archive/refs/tags
PLUGIN_FILEMANAGER_DIR:=$(SOURCE_DIR)/rutorrent-filemanager-$(subst v,,$(PLUGIN_FILEMANAGER_VERSION))

# freetz-filemanager plugin (Freetz-NG enhanced version with p7zip RAR support)
PLUGIN_FREETZ_FILEMANAGER_VERSION:=v1.0.0
PLUGIN_FREETZ_FILEMANAGER_SOURCE:=ircama-rutorrent-freetz-filemanager-$(PLUGIN_FREETZ_FILEMANAGER_VERSION).tar.gz
PLUGIN_FREETZ_FILEMANAGER_HASH:=a6c3885de7faa4fe8db1723279e1ee375854dc982559cfbdb80af751c6be640f
PLUGIN_FREETZ_FILEMANAGER_SITE:=https://github.com/Ircama/rutorrent-freetz-filemanager/archive/refs/tags
PLUGIN_FREETZ_FILEMANAGER_DIR:=$(SOURCE_DIR)/rutorrent-freetz-filemanager-$(subst v,,$(PLUGIN_FREETZ_FILEMANAGER_VERSION))

# filemanager-media plugin
PLUGIN_MEDIASTREAM_VERSION:=master
PLUGIN_MEDIASTREAM_SOURCE:=nelu-rutorrent-filemanager-media-$(PLUGIN_MEDIASTREAM_VERSION).tar.gz
PLUGIN_MEDIASTREAM_HASH:=56d1d28806f8e20b665ac971ed310bcbd4470a5d4876f216340764821bd33147
PLUGIN_MEDIASTREAM_SITE:=https://github.com/nelu/rutorrent-filemanager-media/archive/refs/heads
PLUGIN_MEDIASTREAM_DIR:=$(SOURCE_DIR)/rutorrent-filemanager-media-$(PLUGIN_MEDIASTREAM_VERSION)

# filemanager-share plugin
PLUGIN_FILESHARE_VERSION:=master
PLUGIN_FILESHARE_SOURCE:=nelu-rutorrent-filemanager-share-$(PLUGIN_FILESHARE_VERSION).tar.gz
PLUGIN_FILESHARE_HASH:=a823fce42586d3f54a0e2473e8a924b01221e103b8a7a97719a0e1b76ef5bb5c
PLUGIN_FILESHARE_SITE:=https://github.com/nelu/rutorrent-filemanager-share/archive/refs/heads
PLUGIN_FILESHARE_DIR:=$(SOURCE_DIR)/rutorrent-filemanager-share-$(PLUGIN_FILESHARE_VERSION)

# logoff plugin
PLUGIN_LOGOFF_VERSION:=main
PLUGIN_LOGOFF_SOURCE:=quickbox-rutorrent-logoff-$(PLUGIN_LOGOFF_VERSION).tar.gz
PLUGIN_LOGOFF_HASH:=89e6f2e0b9658857594961bcd6f15a8370158cf5f95c9ddf1ac5d90ca8666c4d
PLUGIN_LOGOFF_SITE:=https://github.com/QuickBox/rutorrent_logoff/archive/refs/heads
PLUGIN_LOGOFF_DIR:=$(SOURCE_DIR)/rutorrent_logoff-$(PLUGIN_LOGOFF_VERSION)

# pause plugin
PLUGIN_PAUSE_VERSION:=master
PLUGIN_PAUSE_SOURCE:=gyran-rutorrent-pausewebui-$(PLUGIN_PAUSE_VERSION).tar.gz
PLUGIN_PAUSE_HASH:=7a6a33d1289a6ef96aebde5aa027bbe7b2255684244708f705409b72b02e3ae8
PLUGIN_PAUSE_SITE:=https://github.com/Gyran/rutorrent-pausewebui/archive/refs/heads
PLUGIN_PAUSE_DIR:=$(SOURCE_DIR)/rutorrent-pausewebui-$(PLUGIN_PAUSE_VERSION)

# instantsearch plugin
PLUGIN_INSTANTSEARCH_VERSION:=master
PLUGIN_INSTANTSEARCH_SOURCE:=gyran-rutorrent-instantsearch-$(PLUGIN_INSTANTSEARCH_VERSION).tar.gz
PLUGIN_INSTANTSEARCH_HASH:=5905a8027d6c31cd85b8b48915885d3e6803e4a23dfc3e4738fc3cbf2725ed6c
PLUGIN_INSTANTSEARCH_SITE:=https://github.com/Gyran/rutorrent-instantsearch/archive/refs/heads
PLUGIN_INSTANTSEARCH_DIR:=$(SOURCE_DIR)/rutorrent-instantsearch-$(PLUGIN_INSTANTSEARCH_VERSION)

# toggle_details_button plugin
PLUGIN_TOGGLEDETAILS_VERSION:=master
PLUGIN_TOGGLEDETAILS_SOURCE:=micdu70-toggle-details-button-$(PLUGIN_TOGGLEDETAILS_VERSION).tar.gz
PLUGIN_TOGGLEDETAILS_HASH:=0d098c4e7b35afcde5eafda649227dd165617f8e9255fa74a8c8b7823e52c072
PLUGIN_TOGGLEDETAILS_SITE:=https://github.com/Micdu70/plugin-toggle_details_button-ruTorrent/archive/refs/heads
PLUGIN_TOGGLEDETAILS_DIR:=$(SOURCE_DIR)/plugin-toggle_details_button-ruTorrent-$(PLUGIN_TOGGLEDETAILS_VERSION)

# trackerstatus plugin
PLUGIN_TRACKERSTATUS_VERSION:=master
PLUGIN_TRACKERSTATUS_SOURCE:=micdu70-rutorrent-trackerstatus-$(PLUGIN_TRACKERSTATUS_VERSION).tar.gz
PLUGIN_TRACKERSTATUS_HASH:=63c820eab1eb6602a2793ba058eebc10cc31338f4f089d2f0d43cc96d9bb3576
PLUGIN_TRACKERSTATUS_SITE:=https://github.com/Micdu70/rutorrent-trackerstatus/archive/refs/heads
PLUGIN_TRACKERSTATUS_DIR:=$(SOURCE_DIR)/rutorrent-trackerstatus-$(PLUGIN_TRACKERSTATUS_VERSION)

$(PKG)_RUTORRENT_WEBDIR:=$($(PKG)_DEST_DIR)/usr/mww/rutorrent

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_BASE_PLUGINS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_TRACKERSTATUS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_FREETZ_FILEMANAGER
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_MEDIASTREAM
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_FILESHARE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_LOGOFF
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_PAUSE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_INSTANTSEARCH
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_RUTORRENT_PLUGIN_TOGGLEDETAILS

# Intermediate variables to avoid double expansion in shell commands
RUTORRENT_PKG_RUTORRENT_WEBDIR := $($(PKG)_RUTORRENT_WEBDIR)
RUTORRENT_PKG_MAKE_DIR := $($(PKG)_MAKE_DIR)
RUTORRENT_PKG_SOURCE := $($(PKG)_SOURCE)
RUTORRENT_PKG_VERSION := $($(PKG)_VERSION)
RUTORRENT_SITE := $($(PKG)_SITE)
RUTORRENT_HASH := $($(PKG)_HASH)

# Download ruTorrent source.
# Upstream asset name is "v<version>.tar.gz", but we store it locally using a unique
# Freetz-style filename to avoid collisions with other packages.
$(DL_DIR)/$(RUTORRENT_PKG_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(RUTORRENT_PKG_SOURCE) $(DL_DIR) v$(RUTORRENT_PKG_VERSION).tar.gz $(RUTORRENT_SITE) $(RUTORRENT_HASH)

$(PKG_UNPACKED)

# Download 3rd party plugins
# Note: Using -o (output filename) to avoid conflicts with generic names like v1.0.0.tar.gz or master.tar.gz
# Each plugin gets a unique filename: repository-plugin-version.tar.gz

# Download 3rd party plugins
$(DL_DIR)/$(AUTODL_RUTORRENT_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(AUTODL_RUTORRENT_SOURCE) $(DL_DIR) v$(AUTODL_RUTORRENT_VERSION).tar.gz $(AUTODL_RUTORRENT_SITE) $(AUTODL_RUTORRENT_HASH)

$(DL_DIR)/$(PLUGIN_MOBILE_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_MOBILE_SOURCE) $(DL_DIR) $(PLUGIN_MOBILE_VERSION).tar.gz $(PLUGIN_MOBILE_SITE) $(PLUGIN_MOBILE_HASH)

$(DL_DIR)/$(PLUGIN_NELU_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_NELU_SOURCE) $(DL_DIR) $(PLUGIN_NELU_VERSION).tar.gz $(PLUGIN_NELU_SITE) $(PLUGIN_NELU_HASH)

$(DL_DIR)/$(PLUGIN_FILEMANAGER_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_FILEMANAGER_SOURCE) $(DL_DIR) $(PLUGIN_FILEMANAGER_VERSION).tar.gz $(PLUGIN_FILEMANAGER_SITE) $(PLUGIN_FILEMANAGER_HASH)

$(DL_DIR)/$(PLUGIN_FREETZ_FILEMANAGER_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_FREETZ_FILEMANAGER_SOURCE) $(DL_DIR) $(PLUGIN_FREETZ_FILEMANAGER_VERSION).tar.gz $(PLUGIN_FREETZ_FILEMANAGER_SITE) $(PLUGIN_FREETZ_FILEMANAGER_HASH)

ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_MEDIASTREAM)),y)
$(DL_DIR)/$(PLUGIN_MEDIASTREAM_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_MEDIASTREAM_SOURCE) $(DL_DIR) $(PLUGIN_MEDIASTREAM_VERSION).tar.gz $(PLUGIN_MEDIASTREAM_SITE) $(PLUGIN_MEDIASTREAM_HASH)
endif

ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_FILESHARE)),y)
$(DL_DIR)/$(PLUGIN_FILESHARE_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_FILESHARE_SOURCE) $(DL_DIR) $(PLUGIN_FILESHARE_VERSION).tar.gz $(PLUGIN_FILESHARE_SITE) $(PLUGIN_FILESHARE_HASH)
endif

ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_LOGOFF)),y)
$(DL_DIR)/$(PLUGIN_LOGOFF_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_LOGOFF_SOURCE) $(DL_DIR) $(PLUGIN_LOGOFF_VERSION).tar.gz $(PLUGIN_LOGOFF_SITE) $(PLUGIN_LOGOFF_HASH)
endif

ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_PAUSE)),y)
$(DL_DIR)/$(PLUGIN_PAUSE_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_PAUSE_SOURCE) $(DL_DIR) $(PLUGIN_PAUSE_VERSION).tar.gz $(PLUGIN_PAUSE_SITE) $(PLUGIN_PAUSE_HASH)
endif

ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_INSTANTSEARCH)),y)
$(DL_DIR)/$(PLUGIN_INSTANTSEARCH_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_INSTANTSEARCH_SOURCE) $(DL_DIR) $(PLUGIN_INSTANTSEARCH_VERSION).tar.gz $(PLUGIN_INSTANTSEARCH_SITE) $(PLUGIN_INSTANTSEARCH_HASH)
endif

ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_TOGGLEDETAILS)),y)
$(DL_DIR)/$(PLUGIN_TOGGLEDETAILS_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_TOGGLEDETAILS_SOURCE) $(DL_DIR) $(PLUGIN_TOGGLEDETAILS_VERSION).tar.gz $(PLUGIN_TOGGLEDETAILS_SITE) $(PLUGIN_TOGGLEDETAILS_HASH)
endif

ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_TRACKERSTATUS)),y)
$(DL_DIR)/$(PLUGIN_TRACKERSTATUS_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(PLUGIN_TRACKERSTATUS_SOURCE) $(DL_DIR) $(PLUGIN_TRACKERSTATUS_VERSION).tar.gz $(PLUGIN_TRACKERSTATUS_SITE) $(PLUGIN_TRACKERSTATUS_HASH)
endif

$(pkg)-precompiled: $($(PKG)_RUTORRENT_WEBDIR)/.installed

# Install ruTorrent
$($(PKG)_RUTORRENT_WEBDIR)/.installed: $(DL_DIR)/$(RUTORRENT_PKG_SOURCE) \
		$(DL_DIR)/$(AUTODL_RUTORRENT_SOURCE) \
		$(DL_DIR)/$(PLUGIN_MOBILE_SOURCE) \
		$(DL_DIR)/$(PLUGIN_NELU_SOURCE) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_FREETZ_FILEMANAGER),$(DL_DIR)/$(PLUGIN_FREETZ_FILEMANAGER_SOURCE),$(DL_DIR)/$(PLUGIN_FILEMANAGER_SOURCE)) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_MEDIASTREAM),$(DL_DIR)/$(PLUGIN_MEDIASTREAM_SOURCE)) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_FILESHARE),$(DL_DIR)/$(PLUGIN_FILESHARE_SOURCE)) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_LOGOFF),$(DL_DIR)/$(PLUGIN_LOGOFF_SOURCE)) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_PAUSE),$(DL_DIR)/$(PLUGIN_PAUSE_SOURCE)) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_INSTANTSEARCH),$(DL_DIR)/$(PLUGIN_INSTANTSEARCH_SOURCE)) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_TOGGLEDETAILS),$(DL_DIR)/$(PLUGIN_TOGGLEDETAILS_SOURCE)) \
		$(if $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_TRACKERSTATUS),$(DL_DIR)/$(PLUGIN_TRACKERSTATUS_SOURCE))
	$(call UNPACK_TARBALL,$(DL_DIR)/$(RUTORRENT_PKG_SOURCE),$(SOURCE_DIR))
	mkdir -p $(RUTORRENT_PKG_RUTORRENT_WEBDIR)
	# Copy ruTorrent core files
	cp -a $(RUTORRENT_DIR)/* $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_BASE_PLUGINS)),y)
	# Keep all official ruTorrent plugins
	@echo ">>> Installing ruTorrent with base plugins..." $(SILENT)
else
	# Remove all plugins - install only ruTorrent core
	@echo ">>> Installing ruTorrent without base plugins..." $(SILENT)
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/*
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_FREETZ_FILEMANAGER)),y)
	# Remove filemanager from base plugins since we'll install the enhanced version
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/filemanager
endif
	# Override settings.php with rTorrent 0.16+ compatible version (removes obsolete to_kb test)
	cp $(RUTORRENT_PKG_MAKE_DIR)/files/rutorrent/settings.php $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/php/settings.php
	# Remove unnecessary files
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/.git*
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/.github
	$(RM) -f $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/.gitignore
	$(RM) -f $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/.gitattributes
	# Install 3rd party plugins
	@echo ">>> Installing 3rd party plugins..." $(SILENT)
	# autodl-irssi plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(AUTODL_RUTORRENT_SOURCE),$(SOURCE_DIR))
	cp -a $(AUTODL_RUTORRENT_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/autodl-irssi
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/autodl-irssi/.git*
	# rutorrentMobile plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_MOBILE_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_MOBILE_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/mobile
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/mobile/.git*
	# nelu thirdparty plugins (extract once, copy multiple plugins)
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_NELU_SOURCE),$(SOURCE_DIR))
	@if [ -d "$(PLUGIN_NELU_DIR)/chat" ]; then \
		cp -a $(PLUGIN_NELU_DIR)/chat $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/; \
		$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/chat/.git*; \
	fi
	@if [ -d "$(PLUGIN_NELU_DIR)/nfo" ]; then \
		cp -a $(PLUGIN_NELU_DIR)/nfo $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/; \
		$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/nfo/.git*; \
	fi
	@if [ -d "$(PLUGIN_NELU_DIR)/hostname" ]; then \
		cp -a $(PLUGIN_NELU_DIR)/hostname $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/; \
		$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/hostname/.git*; \
	fi
	# filemanager plugin
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_FREETZ_FILEMANAGER)),y)
	# freetz-filemanager (Freetz-NG enhanced version with p7zip RAR support and BusyBox compatibility)
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_FREETZ_FILEMANAGER_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_FREETZ_FILEMANAGER_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/filemanager
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/filemanager/.git*
	chmod 755 $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/filemanager/scripts/* 2>/dev/null || true
else
	# Original filemanager plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_FILEMANAGER_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_FILEMANAGER_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/filemanager
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/filemanager/.git*
	chmod 755 $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/filemanager/scripts/* 2>/dev/null || true
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_MEDIASTREAM)),y)
	# mediastream plugin (filemanager-media)
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_MEDIASTREAM_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_MEDIASTREAM_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/mediastream
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/mediastream/.git*
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_FILESHARE)),y)
	# fileshare plugin (filemanager-share)
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_FILESHARE_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_FILESHARE_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/fileshare
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/fileshare/.git*
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_LOGOFF)),y)
	# logoff plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_LOGOFF_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_LOGOFF_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/logoff
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/logoff/.git*
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_PAUSE)),y)
	# pause plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_PAUSE_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_PAUSE_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/pausewebui
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/pausewebui/.git*
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_INSTANTSEARCH)),y)
	# instantsearch plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_INSTANTSEARCH_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_INSTANTSEARCH_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/instantsearch
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/instantsearch/.git*
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_TOGGLEDETAILS)),y)
	# toggle_details_button plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_TOGGLEDETAILS_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_TOGGLEDETAILS_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/toggle_details_button
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/toggle_details_button/.git*
endif
ifeq ($(strip $(FREETZ_PACKAGE_RUTORRENT_PLUGIN_TRACKERSTATUS)),y)
	# trackerstatus plugin
	$(call UNPACK_TARBALL,$(DL_DIR)/$(PLUGIN_TRACKERSTATUS_SOURCE),$(SOURCE_DIR))
	cp -a $(PLUGIN_TRACKERSTATUS_DIR) $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/trackerstatus
	$(RM) -rf $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins/trackerstatus/.git*
endif
	# Add include of freetz_config.php to config.php for dynamic SCGI socket configuration
	# Insert after the opening <?php tag
	@if ! grep -q "freetz_config.php" $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/conf/config.php 2>/dev/null; then \
		sed -i '1 a // Freetz-NG dynamic SCGI configuration\nrequire_once(__DIR__ . "/freetz_config.php");' \
			$(RUTORRENT_PKG_RUTORRENT_WEBDIR)/conf/config.php; \
	fi
	# Verify plugins directory exists
	@if [ ! -d "$(RUTORRENT_PKG_RUTORRENT_WEBDIR)/plugins" ]; then \
		echo "ERROR: ruTorrent plugins directory not found!"; \
		exit 1; \
	fi
	# Copy Freetz-specific runtime helpers without overriding upstream index.html.
	@for overlay in conf index.php php-info.php rtorrent_xmlrpc_proxy.php share; do \
		if [ -e "$(RUTORRENT_PKG_MAKE_DIR)/files/root/usr/mww/rutorrent/$$overlay" ]; then \
			cp -a $(RUTORRENT_PKG_MAKE_DIR)/files/root/usr/mww/rutorrent/$$overlay $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/; \
		fi; \
	done
	@if ! grep -q "auth_ping=1" $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/index.html 2>/dev/null; then \
		sed -i '/cache-control/r $(RUTORRENT_PKG_MAKE_DIR)/files/index.auth-guard.html' \
			$(RUTORRENT_PKG_RUTORRENT_WEBDIR)/index.html; \
	fi
	# Fix permissions for ruTorrent share directory
	# Ensure torrents directory has world-writable permissions so webserver can write torrents
	@if [ -d "$(RUTORRENT_PKG_RUTORRENT_WEBDIR)/share/users/admin" ]; then \
		mkdir -p $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/share/users/admin/torrents; \
		chmod 1777 $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/share/users/admin/torrents; \
	fi
	# Fix permissions for ruTorrent conf directory
	# Ensure conf files have read-write permissions so web interface can modify them
	@if [ -d "$(RUTORRENT_PKG_RUTORRENT_WEBDIR)/conf" ]; then \
		chmod a+rw $(RUTORRENT_PKG_RUTORRENT_WEBDIR)/conf/*; \
	fi
	@echo ">>> ruTorrent web interface installed successfully" $(SILENT)
	touch $@

$(pkg):

$(pkg)-uninstall:
	$(RM) -r $(RUTORRENT_PKG_RUTORRENT_WEBDIR)

$(PKG_FINISH)
