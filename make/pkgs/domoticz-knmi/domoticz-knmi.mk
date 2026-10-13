$(call PKG_INIT_BIN, 9f6de271e8624c52bbf4d14ec313be3906a6aa90)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree
# (esp-serial-flasher for snapshots, domoticz-homewizard-p1 for the plugins).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ff9d79ce4a921e2e9cab8cc9c5e194eaf55fc274c207c58409436f7e8b385783
$(PKG)_SITE:=https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin/archive
### WEBSITE:=https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin
### CHANGES:=https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin/commits
### CVSREPO:=https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/Domoticz-KNMI-Weather-Plugin
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_KNMI

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: its Python modules (the helpers of the
# repository are imported by plugin.py), the translations and the upstream
# README/LICENSE. The images and the release archives of the repository are not
# installed.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_KNMI_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_KNMI_DIR)/plugin.py \
		$(DOMOTICZ_KNMI_DIR)/README.md \
		$(DOMOTICZ_KNMI_DIR)/LICENSE \
		$(DOMOTICZ_KNMI_PLUGIN_DIR)/
	chmod 644 $(DOMOTICZ_KNMI_PLUGIN_DIR)/*

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_KNMI_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
