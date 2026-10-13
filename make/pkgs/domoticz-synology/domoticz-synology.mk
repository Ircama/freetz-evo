$(call PKG_INIT_BIN, 3fb627ad93cd5ff856cb4c805b9e005bb18e7c1a)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree
# (esp-serial-flasher for snapshots, domoticz-homewizard-p1 for the plugins).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=5fe8998e5283d743d35331dd4abab7b5bbc807b98abe6e2b9176453f80a7db9b
$(PKG)_SITE:=https://github.com/lolautruche/SurveillanceStationDomoticz/archive
### WEBSITE:=https://github.com/lolautruche/SurveillanceStationDomoticz
### CHANGES:=https://github.com/lolautruche/SurveillanceStationDomoticz/commits
### CVSREPO:=https://github.com/lolautruche/SurveillanceStationDomoticz
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/SurveillanceStationDomoticz
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_SYNOLOGY

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: its Python modules (the helpers of the
# repository are imported by plugin.py), the translations and the upstream
# README/LICENSE. The images and the release archives of the repository are not
# installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_SYNOLOGY_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_SYNOLOGY_DIR)/plugin.py \
		$(DOMOTICZ_SYNOLOGY_DIR)/README.md \
		$(DOMOTICZ_SYNOLOGY_DIR)/LICENSE \
		$(DOMOTICZ_SYNOLOGY_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_SYNOLOGY_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_SYNOLOGY_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
