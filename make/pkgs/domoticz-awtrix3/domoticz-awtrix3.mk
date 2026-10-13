$(call PKG_INIT_BIN, 6179552d7382908491a86fd58b391dc329f85304)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree.
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=aaa485c97e6c71af49264c6e5c80d602b6a48edca2d7afa3aa0cd1793bbf9956
$(PKG)_SITE:=https://github.com/galadril/Domoticz-AWTRIX3-Plugin/archive
### WEBSITE:=https://github.com/galadril/Domoticz-AWTRIX3-Plugin
### CHANGES:=https://github.com/galadril/Domoticz-AWTRIX3-Plugin/commits
### CVSREPO:=https://github.com/galadril/Domoticz-AWTRIX3-Plugin
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/Domoticz-AWTRIX3-Plugin
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-requests
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_AWTRIX3

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: the Python modules of the repository
# (`plugin.py` and the helpers it imports), the upstream documentation and the resource directories icons, images of the project.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_AWTRIX3_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_AWTRIX3_DIR)/plugin.py \
		$(DOMOTICZ_AWTRIX3_DIR)/README.md \
		$(DOMOTICZ_AWTRIX3_DIR)/LICENSE.txt \
		$(DOMOTICZ_AWTRIX3_PLUGIN_DIR)/
	cp -r \
		$(DOMOTICZ_AWTRIX3_DIR)/icons/ \
		$(DOMOTICZ_AWTRIX3_DIR)/images/ \
		$(DOMOTICZ_AWTRIX3_PLUGIN_DIR)/
# Only the files are made world readable: chmod on a glob would clear the execute
# bit of the resource directories, which Python needs to traverse them.
	find $(DOMOTICZ_AWTRIX3_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_AWTRIX3_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
