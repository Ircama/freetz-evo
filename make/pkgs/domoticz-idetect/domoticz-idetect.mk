$(call PKG_INIT_BIN, 200c6d444023c7acec469fdc6627fb7fbc2e9fa0)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree
# (esp-serial-flasher for snapshots, domoticz-homewizard-p1 for the plugins).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=1efefbda8559f03c2ee61962451ae4c508f7deebbb97b0f975786aeacfe4350b
$(PKG)_SITE:=https://github.com/d-EScape/Domoticz_iDetect/archive
### WEBSITE:=https://github.com/d-EScape/Domoticz_iDetect
### CHANGES:=https://github.com/d-EScape/Domoticz_iDetect/commits
### CVSREPO:=https://github.com/d-EScape/Domoticz_iDetect
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/Domoticz_iDetect
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-fritzconnection
$(PKG)_DEPENDS_ON += python3-paramiko
$(PKG)_DEPENDS_ON += python3-pynetgear
$(PKG)_DEPENDS_ON += python3-requests
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_IDETECT

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: plugin.py and override_switch.py (the
# switch that overrides the detection), the trackers and the helpers that
# plugin.py imports, the images README.md refers to and the README itself. The
# systemd units of the repository (i*.zip) and .gitignore are not installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_IDETECT_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_IDETECT_DIR)/plugin.py \
		$(DOMOTICZ_IDETECT_DIR)/override_switch.py \
		$(DOMOTICZ_IDETECT_DIR)/README.md \
		$(DOMOTICZ_IDETECT_PLUGIN_DIR)/
	cp -r \
		$(DOMOTICZ_IDETECT_DIR)/helpers/ \
		$(DOMOTICZ_IDETECT_DIR)/trackers/ \
		$(DOMOTICZ_IDETECT_DIR)/resources/ \
		$(DOMOTICZ_IDETECT_PLUGIN_DIR)/
# Only the files are made world readable: chmod on the glob would clear the
# execute bit of helpers/, trackers/ and resources/, which Python needs to
# traverse the directories when it imports the modules inside them.
	find $(DOMOTICZ_IDETECT_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_IDETECT_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
