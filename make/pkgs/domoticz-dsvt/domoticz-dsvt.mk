$(call PKG_INIT_BIN, 8fd2ef3fbd467e5623eb4e71fc302b35b904a24d)
# Upstream has no release tags, so the version is the commit of the main branch
# (same convention as esp-serial-flasher and domoticz-homewizard-p1).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=c79cc8b401ec49da323d9740aa9a1d6fdb0c77132c10cb1a4b4eb19f664b6a90
$(PKG)_SITE:=https://github.com/szelessavalapitvany/Domoticz-DSVT/archive
### WEBSITE:=https://github.com/szelessavalapitvany/Domoticz-DSVT
### CHANGES:=https://github.com/szelessavalapitvany/Domoticz-DSVT/commits/main
### CVSREPO:=https://github.com/szelessavalapitvany/Domoticz-DSVT
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

# The GitHub archive unpacks to Domoticz-DSVT-<commit>/, while freetz expects the
# sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Domoticz loads its python plugins from <approot>/plugins/<directory>/plugin.py
# and the init script of the domoticz package passes -approot /usr/share/domoticz.
# That directory is owned by the domoticz package, whose external handling moves
# the whole /usr/share/domoticz tree and leaves a symlink at the original path:
# the plugin therefore needs no external entry of its own. The plugin directory
# name is the one upstream uses in its installation instructions.
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/DSVT_HMV_ZONE_12
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

# Upstream also copies viewer/* into the www templates directory of Domoticz:
# the zone dashboard page is served from there (the two html/json/js files).
$(PKG)_VIEWER_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/www/templates
$(PKG)_VIEWER_STAMP:=$($(PKG)_VIEWER_DIR)/DSVT_HMV_ZONE_12.html

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_DSVT

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# plugin.py, the translations (read from the plugin directory through
# Parameters["HomeFolder"]), the upstream README and the MIT LICENSE are
# installed; docs/ is only the documentation of the GitHub page.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_DSVT_PLUGIN_DIR)
	cp $(DOMOTICZ_DSVT_DIR)/plugin.py \
		$(DOMOTICZ_DSVT_DIR)/README.md \
		$(DOMOTICZ_DSVT_DIR)/LICENSE \
		$(DOMOTICZ_DSVT_DIR)/dsvt_translate_*.json \
		$(DOMOTICZ_DSVT_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_DSVT_PLUGIN_DIR)/*

$($(PKG)_VIEWER_STAMP): $($(PKG)_PLUGIN_STAMP)
	mkdir -p $(DOMOTICZ_DSVT_VIEWER_DIR)
	cp $(DOMOTICZ_DSVT_DIR)/viewer/* $(DOMOTICZ_DSVT_VIEWER_DIR)/
	chmod 644 $(DOMOTICZ_DSVT_VIEWER_DIR)/DSVT_* $(DOMOTICZ_DSVT_VIEWER_DIR)/dsvt_*

$(pkg): $($(PKG)_PLUGIN_STAMP) $($(PKG)_VIEWER_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP) $($(PKG)_VIEWER_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_DSVT_PLUGIN_DIR)
	$(RM) $(DOMOTICZ_DSVT_VIEWER_DIR)/DSVT_HMV_ZONE_12.html \
		$(DOMOTICZ_DSVT_VIEWER_DIR)/dsvt_hmv_zone_12_viewer.js \
		$(DOMOTICZ_DSVT_VIEWER_DIR)/dsvt_html_translate_*.json

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
