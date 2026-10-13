$(call PKG_INIT_BIN, cc10256dce9e448e26e362d88f64daad5b1ec391)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree
# (esp-serial-flasher for snapshots, domoticz-homewizard-p1 for the plugins).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=305c491d9e50da74b52bd722bf6733dd60e83e39acaa095f93f7244102aa852d
$(PKG)_SITE:=https://github.com/mvzut/maxcube-Domoticz-plugin/archive
### WEBSITE:=https://github.com/mvzut/maxcube-Domoticz-plugin
### CHANGES:=https://github.com/mvzut/maxcube-Domoticz-plugin/commits
### CVSREPO:=https://github.com/mvzut/maxcube-Domoticz-plugin
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/maxcube-Domoticz-plugin
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_MAXCUBE

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: its Python modules (the helpers of the
# repository are imported by plugin.py), the translations and the upstream
# README/LICENSE. The images and the release archives of the repository are not
# installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_MAXCUBE_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_MAXCUBE_DIR)/plugin.py \
		$(DOMOTICZ_MAXCUBE_DIR)/README.md \
		$(DOMOTICZ_MAXCUBE_PLUGIN_DIR)/
	cp -r \
		$(DOMOTICZ_MAXCUBE_DIR)/maxcube/ \
		$(DOMOTICZ_MAXCUBE_PLUGIN_DIR)/
# Only the files are made world readable: chmod on the glob would clear the
# execute bit of maxcube/, which Python needs to traverse the directory when
# it imports the modules inside it.
	find $(DOMOTICZ_MAXCUBE_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_MAXCUBE_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
