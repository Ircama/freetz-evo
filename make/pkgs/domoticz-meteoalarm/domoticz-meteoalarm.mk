$(call PKG_INIT_BIN, 6049a349a427721938a9837429dfd66f2c4aff8c)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree.
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=52ef6f2a86bca64d0bb35a1b4344052e8cf6835576ba85a0268aa1af65ea1d6a
$(PKG)_SITE:=https://github.com/ycahome/MeteoAlarmEU/archive
### WEBSITE:=https://github.com/ycahome/MeteoAlarmEU
### CHANGES:=https://github.com/ycahome/MeteoAlarmEU/commits
### CVSREPO:=https://github.com/ycahome/MeteoAlarmEU
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/MeteoAlarmEU
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-feedparser
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_METEOALARM

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: the Python modules of the repository
# (`plugin.py` and the helpers it imports), the upstream documentation.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_METEOALARM_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_METEOALARM_DIR)/plugin.py \
		$(DOMOTICZ_METEOALARM_DIR)/README.md \
		$(DOMOTICZ_METEOALARM_DIR)/LICENSE \
		$(DOMOTICZ_METEOALARM_PLUGIN_DIR)/
# Only the files are made world readable: chmod on a glob would clear the execute
# bit of the resource directories, which Python needs to traverse them.
	find $(DOMOTICZ_METEOALARM_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_METEOALARM_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
