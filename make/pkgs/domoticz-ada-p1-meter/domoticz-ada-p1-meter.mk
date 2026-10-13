$(call PKG_INIT_BIN, 98d13746372fd75d29fed3a37589244f5b98bff9)
# Upstream has no release tags, so the version is the commit of the main branch
# (same convention as esp-serial-flasher and domoticz-homewizard-p1).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=605d1b26f10b35886d1923b3f47e566748cbe4dec2c73b930a9a7fd376d369fa
$(PKG)_SITE:=https://github.com/szelessavalapitvany/ADA_P1_meter_for_Domoticz/archive
### WEBSITE:=https://github.com/szelessavalapitvany/ADA_P1_meter_for_Domoticz
### CHANGES:=https://github.com/szelessavalapitvany/ADA_P1_meter_for_Domoticz/commits/main
### CVSREPO:=https://github.com/szelessavalapitvany/ADA_P1_meter_for_Domoticz
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

# The GitHub archive unpacks to ADA_P1_meter_for_Domoticz-<commit>/, while freetz
# expects the sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Domoticz loads its python plugins from <approot>/plugins/<directory>/plugin.py
# and the init script of the domoticz package passes -approot /usr/share/domoticz.
# That directory is owned by the domoticz package, whose external handling moves
# the whole /usr/share/domoticz tree and leaves a symlink at the original path:
# the plugin therefore needs no external entry of its own.
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/ADA_P1_meter_for_Domoticz
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_ADA_P1_METER

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# plugin.py, the 17 translation files (read from the plugin directory through
# Parameters["HomeFolder"]) and the upstream README are installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_ADA_P1_METER_PLUGIN_DIR)
	cp $(DOMOTICZ_ADA_P1_METER_DIR)/plugin.py \
		$(DOMOTICZ_ADA_P1_METER_DIR)/README.md \
		$(DOMOTICZ_ADA_P1_METER_DIR)/ada_translate_*.json \
		$(DOMOTICZ_ADA_P1_METER_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_ADA_P1_METER_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_ADA_P1_METER_PLUGIN_DIR)

$(pkg)-uninstall:
	$(RM) -r $(DOMOTICZ_ADA_P1_METER_PLUGIN_DIR)

$(PKG_FINISH)
