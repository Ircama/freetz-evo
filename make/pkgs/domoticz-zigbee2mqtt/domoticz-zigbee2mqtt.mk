$(call PKG_INIT_BIN, 660db3f68ae48fedce9b17727db4617ec5f721c8)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree.
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=1dab62d855977ce8a6406ff28663c2baa0be2e1942f701b4dd7481339520ccfc
$(PKG)_SITE:=https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin/archive
### WEBSITE:=https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin
### CHANGES:=https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin/commits
### CVSREPO:=https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/zigbee2mqtt
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-requests
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_ZIGBEE2MQTT

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: the Python modules of the repository
# (`plugin.py` and the helpers it imports), the upstream documentation and the resource directories adapters, api, devices, features, frontend of the project.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_ZIGBEE2MQTT_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/adapter.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/blacklist.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/bridge.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/configuration.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/devices_manager.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/domoticz.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/feature_utils.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/groups_manager.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/mqtt.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/plugin.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/zigbee_message.py \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/README.md \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/LICENSE \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/CHANGELOG.md \
		$(DOMOTICZ_ZIGBEE2MQTT_PLUGIN_DIR)/
	cp -r \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/adapters/ \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/api/ \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/devices/ \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/features/ \
		$(DOMOTICZ_ZIGBEE2MQTT_DIR)/frontend/ \
		$(DOMOTICZ_ZIGBEE2MQTT_PLUGIN_DIR)/
# Only the files are made world readable: chmod on a glob would clear the execute
# bit of the resource directories, which Python needs to traverse them.
	find $(DOMOTICZ_ZIGBEE2MQTT_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_ZIGBEE2MQTT_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
