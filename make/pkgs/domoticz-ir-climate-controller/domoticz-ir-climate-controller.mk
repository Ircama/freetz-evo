$(call PKG_INIT_BIN, 0ccccae04866596f0c29e2c475bf336827909b30)
# Upstream has no release tags, so the version is the commit of the main branch
# (same convention as esp-serial-flasher and domoticz-homewizard-p1).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b386195d89af4cba926b99ee185c3b615a74c9f85784ecc437e9d4e7041c8fa8
$(PKG)_SITE:=https://github.com/szelessavalapitvany/domoticz-ir-climate-controller/archive
### WEBSITE:=https://github.com/szelessavalapitvany/domoticz-ir-climate-controller
### CHANGES:=https://github.com/szelessavalapitvany/domoticz-ir-climate-controller/commits/main
### CVSREPO:=https://github.com/szelessavalapitvany/domoticz-ir-climate-controller
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

# The GitHub archive unpacks to domoticz-ir-climate-controller-<commit>/, while
# freetz expects the sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Domoticz loads its python plugins from <approot>/plugins/<directory>/plugin.py
# and the init script of the domoticz package passes -approot /usr/share/domoticz.
# That directory is owned by the domoticz package, whose external handling moves
# the whole /usr/share/domoticz tree and leaves a symlink at the original path:
# the plugin therefore needs no external entry of its own. The directory name is
# the one upstream uses in its installation instructions.
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/IR_climate_controller
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_IR_CLIMATE_CONTROLLER

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# plugin.py, the 17 translation files (read from the plugin directory through
# Parameters["HomeFolder"]) and the upstream README are installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_IR_CLIMATE_CONTROLLER_PLUGIN_DIR)
	cp $(DOMOTICZ_IR_CLIMATE_CONTROLLER_DIR)/plugin.py \
		$(DOMOTICZ_IR_CLIMATE_CONTROLLER_DIR)/README.md \
		$(DOMOTICZ_IR_CLIMATE_CONTROLLER_DIR)/icc_translate_*.json \
		$(DOMOTICZ_IR_CLIMATE_CONTROLLER_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_IR_CLIMATE_CONTROLLER_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_IR_CLIMATE_CONTROLLER_PLUGIN_DIR)

$(pkg)-uninstall:
	$(RM) -r $(DOMOTICZ_IR_CLIMATE_CONTROLLER_PLUGIN_DIR)

$(PKG_FINISH)
