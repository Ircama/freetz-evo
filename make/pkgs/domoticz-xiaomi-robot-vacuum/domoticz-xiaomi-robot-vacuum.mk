$(call PKG_INIT_BIN, 9791b046a63ed9a76438297c4cad4f88c534e1c4)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree.
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=9977a2a06688bb1abfeb377394f81d3828b6200324e312cb375a02a309c2a3d4
$(PKG)_SITE:=https://github.com/mrin/domoticz-mirobot-plugin/archive
### WEBSITE:=https://github.com/mrin/domoticz-mirobot-plugin
### CHANGES:=https://github.com/mrin/domoticz-mirobot-plugin/commits
### CVSREPO:=https://github.com/mrin/domoticz-mirobot-plugin
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

# The GitHub archive unpacks to <repository>-<commit>/, while freetz expects the
# sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Domoticz loads its python plugins from <approot>/plugins/<directory>/plugin.py
# and the init script of the domoticz package passes -approot /usr/share/domoticz.
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/xiaomi-mirobot
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-gevent
$(PKG)_DEPENDS_ON += python3-msgpack
$(PKG)_DEPENDS_ON += python3-miio
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_XIAOMI_ROBOT_VACUUM

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: the Python modules of the repository
# and the upstream documentation.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_XIAOMI_ROBOT_VACUUM_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_XIAOMI_ROBOT_VACUUM_DIR)/README.md \
		$(DOMOTICZ_XIAOMI_ROBOT_VACUUM_DIR)/miio_server.py \
		$(DOMOTICZ_XIAOMI_ROBOT_VACUUM_DIR)/miio_server.sh \
		$(DOMOTICZ_XIAOMI_ROBOT_VACUUM_DIR)/plugin.py \
		$(DOMOTICZ_XIAOMI_ROBOT_VACUUM_PLUGIN_DIR)/
# Only the files are made world readable: chmod on a glob would clear the execute
# bit of the resource directories, which Python needs to traverse them.
	find $(DOMOTICZ_XIAOMI_ROBOT_VACUUM_PLUGIN_DIR) -type f -exec chmod 644 {} \;
# miio_server.sh starts the helper server, so it has to stay executable.
	chmod 755 $(DOMOTICZ_XIAOMI_ROBOT_VACUUM_PLUGIN_DIR)/miio_server.sh

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_XIAOMI_ROBOT_VACUUM_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
