$(call PKG_INIT_BIN, c436a1327d098327768c85c8e7e0185c2b2f6a75)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree
# (esp-serial-flasher for snapshots, domoticz-homewizard-p1 for the plugins).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=7de2590eac2c39cfae4042b324504232573d9219192903b7df3b4d961c32dee9
$(PKG)_SITE:=https://github.com/JanJaapKo/domoticz-GoodWeSEMS/archive
### WEBSITE:=https://github.com/JanJaapKo/domoticz-GoodWeSEMS
### CHANGES:=https://github.com/JanJaapKo/domoticz-GoodWeSEMS/commits
### CVSREPO:=https://github.com/JanJaapKo/domoticz-GoodWeSEMS
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/domoticz-GoodWeSEMS
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-requests
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_GOODWE

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: its Python modules (the helpers of the
# repository are imported by plugin.py), the translations and the upstream
# README/LICENSE. The images and the release archives of the repository are not
# installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_GOODWE_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_GOODWE_DIR)/GoodWe.py \
		$(DOMOTICZ_GOODWE_DIR)/exceptions.py \
		$(DOMOTICZ_GOODWE_DIR)/fakeDomoticz.py \
		$(DOMOTICZ_GOODWE_DIR)/manual_test.py \
		$(DOMOTICZ_GOODWE_DIR)/plugin.py \
		$(DOMOTICZ_GOODWE_DIR)/plugin_test.py \
		$(DOMOTICZ_GOODWE_DIR)/telemetry_manual_test.py \
		$(DOMOTICZ_GOODWE_DIR)/README.md \
		$(DOMOTICZ_GOODWE_DIR)/LICENSE.md \
		$(DOMOTICZ_GOODWE_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_GOODWE_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_GOODWE_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
