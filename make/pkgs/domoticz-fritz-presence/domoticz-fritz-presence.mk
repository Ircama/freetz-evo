$(call PKG_INIT_BIN, 5aefd653e0b09ec9559bb78ae94c11ea52d29bb9)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree
# (esp-serial-flasher for snapshots, domoticz-homewizard-p1 for the plugins).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=74ca9f33c405b86bd0feb3ddd6e0108f5510cb998b40f9bc10396c6255e6dab3
$(PKG)_SITE:=https://github.com/belzetrigger/domoticz-FritzPresence/archive
### WEBSITE:=https://github.com/belzetrigger/domoticz-FritzPresence
### CHANGES:=https://github.com/belzetrigger/domoticz-FritzPresence/commits
### CVSREPO:=https://github.com/belzetrigger/domoticz-FritzPresence
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/domoticz-FritzPresence
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-fritzconnection
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_FRITZ_PRESENCE

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: its Python modules (the helpers of the
# repository are imported by plugin.py), the translations and the upstream
# README/LICENSE. The images and the release archives of the repository are not
# installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_FRITZ_PRESENCE_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_FRITZ_PRESENCE_DIR)/__init__.py \
		$(DOMOTICZ_FRITZ_PRESENCE_DIR)/plugin.py \
		$(DOMOTICZ_FRITZ_PRESENCE_DIR)/README.md \
		$(DOMOTICZ_FRITZ_PRESENCE_DIR)/LICENSE \
		$(DOMOTICZ_FRITZ_PRESENCE_PLUGIN_DIR)/
	cp -r \
		$(DOMOTICZ_FRITZ_PRESENCE_DIR)/blz/ \
		$(DOMOTICZ_FRITZ_PRESENCE_DIR)/fritzhelper/ \
		$(DOMOTICZ_FRITZ_PRESENCE_DIR)/resources/ \
		$(DOMOTICZ_FRITZ_PRESENCE_PLUGIN_DIR)/
# Only the files are made world readable: chmod on the glob would clear the
# execute bit of blz/, fritzhelper/ and resources/, which Python needs to
# traverse the directories when it imports the modules inside them.
	find $(DOMOTICZ_FRITZ_PRESENCE_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_FRITZ_PRESENCE_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
