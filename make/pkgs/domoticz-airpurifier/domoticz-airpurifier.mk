$(call PKG_INIT_BIN, 18a735d1bef45488dec6937a438888e3134e6564)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree
# (esp-serial-flasher for snapshots, domoticz-homewizard-p1 for the plugins).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=30feb058fab247932d5d301a6ca059aa9d8e519b6d8f2599869b215c0e0a73b6
$(PKG)_SITE:=https://github.com/kofec/domoticz-AirPurifier/archive
### WEBSITE:=https://github.com/kofec/domoticz-AirPurifier
### CHANGES:=https://github.com/kofec/domoticz-AirPurifier/commits
### CVSREPO:=https://github.com/kofec/domoticz-AirPurifier
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

# The GitHub archive unpacks to <repository>-<commit>/, while freetz expects the
# sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Domoticz loads its python plugins from <approot>/plugins/<directory>/plugin.py
# and the init script of the domoticz package passes -approot /usr/share/domoticz.
# That directory is owned by the domoticz package, whose external handling moves
# the whole /usr/share/domoticz tree and leaves a symlink at the original path:
# the plugin therefore needs no external entry of its own.
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/domoticz-AirPurifier
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-miio
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_AIRPURIFIER

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: plugin.py, the MyAir.py helper that
# is run as a separate process for every request (it is the only file that
# imports miio) and the upstream README. The repository has no other files.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_AIRPURIFIER_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_AIRPURIFIER_DIR)/plugin.py \
		$(DOMOTICZ_AIRPURIFIER_DIR)/MyAir.py \
		$(DOMOTICZ_AIRPURIFIER_DIR)/README.md \
		$(DOMOTICZ_AIRPURIFIER_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_AIRPURIFIER_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_AIRPURIFIER_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
