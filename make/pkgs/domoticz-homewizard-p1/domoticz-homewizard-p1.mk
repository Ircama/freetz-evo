$(call PKG_INIT_BIN, 117910a0c9d25ca75abf53f015b854dbfbf88dec)
# Upstream has no release tags (and no license file), so the version is the
# commit of the main branch, as done for the other snapshots in this tree
# (esp-serial-flasher, lnav-rs).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f2c419735da4b16e17512e875dc399bf93241417a5072542eda930dd664da67e
$(PKG)_SITE:=https://github.com/szelessavalapitvany/HomeWizard-Wifi-p1-plugin-Extended/archive
### WEBSITE:=https://github.com/szelessavalapitvany/HomeWizard-Wifi-p1-plugin-Extended
### CHANGES:=https://github.com/szelessavalapitvany/HomeWizard-Wifi-p1-plugin-Extended/commits/main
### CVSREPO:=https://github.com/szelessavalapitvany/HomeWizard-Wifi-p1-plugin-Extended
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

# The GitHub archive unpacks to HomeWizard-Wifi-p1-plugin-Extended-<commit>/,
# while freetz expects the sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Domoticz loads its python plugins from <approot>/plugins/<directory>/plugin.py
# and the init script of the domoticz package passes -approot /usr/share/domoticz.
# That directory is owned by the domoticz package, whose external handling moves
# the whole /usr/share/domoticz tree and leaves a symlink at the original path:
# the plugin therefore needs no external entry of its own.
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/HomeWizard-Wifi-p1-plugin-Extended
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_HOMEWIZARD_P1

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# The plugin reads its translation files from its own directory (Parameters
# ["HomeFolder"]), so plugin.py, the 17 homewizard_translate_*.json files and
# the upstream README (it documents the hardware parameters) are installed. The
# screenshots of images/ are not: they are 440 KB of documentation for the
# GitHub page.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_HOMEWIZARD_P1_PLUGIN_DIR)
	cp $(DOMOTICZ_HOMEWIZARD_P1_DIR)/plugin.py \
		$(DOMOTICZ_HOMEWIZARD_P1_DIR)/README.md \
		$(DOMOTICZ_HOMEWIZARD_P1_DIR)/homewizard_translate_*.json \
		$(DOMOTICZ_HOMEWIZARD_P1_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_HOMEWIZARD_P1_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_HOMEWIZARD_P1_PLUGIN_DIR)

$(pkg)-uninstall:
	$(RM) -r $(DOMOTICZ_HOMEWIZARD_P1_PLUGIN_DIR)

$(PKG_FINISH)
