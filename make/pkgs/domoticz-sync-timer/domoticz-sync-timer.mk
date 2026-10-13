$(call PKG_INIT_BIN, 1fe8331b3e879b8c62b3955f305582c7d1028f12)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree.
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=67b71442b7d7956a37eb29b7539d79e04b10d6f4a73935668cf60efbcf4524ad
$(PKG)_SITE:=https://github.com/skarab22/Domoticz-sync-timer/archive
### WEBSITE:=https://github.com/skarab22/Domoticz-sync-timer
### CHANGES:=https://github.com/skarab22/Domoticz-sync-timer/commits
### CVSREPO:=https://github.com/skarab22/Domoticz-sync-timer
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/Update_timer
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-requests
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_SYNC_TIMER

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: the Python modules of the repository
# (`plugin.py` and the helpers it imports), the upstream documentation.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_SYNC_TIMER_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_SYNC_TIMER_DIR)/plugin.py \
		$(DOMOTICZ_SYNC_TIMER_DIR)/README.md \
		$(DOMOTICZ_SYNC_TIMER_PLUGIN_DIR)/
# Only the files are made world readable: chmod on a glob would clear the execute
# bit of the resource directories, which Python needs to traverse them.
	find $(DOMOTICZ_SYNC_TIMER_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_SYNC_TIMER_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
