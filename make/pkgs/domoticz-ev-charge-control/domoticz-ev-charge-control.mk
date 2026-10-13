$(call PKG_INIT_BIN, 844b8d90330c3c6731c9f096ece6ed262740f5e1)
# Upstream has no release tags, so the version is the commit of the main branch
# (same convention as esp-serial-flasher and domoticz-homewizard-p1).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=87c7e5594f20b3c86e590388d7f63bb5f4c98f2586aa1c816165766f6f82d54e
$(PKG)_SITE:=https://github.com/szelessavalapitvany/EV_Charge_Control/archive
### WEBSITE:=https://github.com/szelessavalapitvany/EV_Charge_Control
### CHANGES:=https://github.com/szelessavalapitvany/EV_Charge_Control/commits/main
### CVSREPO:=https://github.com/szelessavalapitvany/EV_Charge_Control
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

# The GitHub archive unpacks to EV_Charge_Control-<commit>/, while freetz expects
# the sources directly in $(PKG)_DIR.
$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Domoticz loads its python plugins from <approot>/plugins/<directory>/plugin.py
# and the init script of the domoticz package passes -approot /usr/share/domoticz.
# That directory is owned by the domoticz package, whose external handling moves
# the whole /usr/share/domoticz tree and leaves a symlink at the original path:
# the plugin therefore needs no external entry of its own.
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/EV_Charge_Control
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_EV_CHARGE_CONTROL

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# plugin.py, the translations (they are read from the plugin directory through
# Parameters["HomeFolder"]), the upstream README and the MIT LICENSE are
# installed. The plugin is small, the payload of the package is about 20 KB.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_EV_CHARGE_CONTROL_PLUGIN_DIR)
	cp $(DOMOTICZ_EV_CHARGE_CONTROL_DIR)/plugin.py \
		$(DOMOTICZ_EV_CHARGE_CONTROL_DIR)/README.md \
		$(DOMOTICZ_EV_CHARGE_CONTROL_DIR)/LICENSE \
		$(DOMOTICZ_EV_CHARGE_CONTROL_DIR)/evcc_translate_*.json \
		$(DOMOTICZ_EV_CHARGE_CONTROL_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_EV_CHARGE_CONTROL_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_EV_CHARGE_CONTROL_PLUGIN_DIR)

$(pkg)-uninstall:
	$(RM) -r $(DOMOTICZ_EV_CHARGE_CONTROL_PLUGIN_DIR)

$(PKG_FINISH)
