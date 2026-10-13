$(call PKG_INIT_BIN, c5053460dd010136cd9d52405351bcb8b63c06c4)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree.
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=eaa36aea50f53068f7b6821d54d63923cd54f16ce3921ec31ff93a172940d45f
$(PKG)_SITE:=https://github.com/stas-demydiuk/domoticz-plugins-manager/archive
### WEBSITE:=https://github.com/stas-demydiuk/domoticz-plugins-manager
### CHANGES:=https://github.com/stas-demydiuk/domoticz-plugins-manager/commits
### CVSREPO:=https://github.com/stas-demydiuk/domoticz-plugins-manager
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/plugins-manager
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-requests
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_PLUGINS_MANAGER

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: the Python modules of the repository
# (`plugin.py` and the helpers it imports), the upstream documentation and the resource directories api, frontend of the project.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_PLUGINS_MANAGER_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_PLUGINS_MANAGER_DIR)/manager.py \
		$(DOMOTICZ_PLUGINS_MANAGER_DIR)/plugin.py \
		$(DOMOTICZ_PLUGINS_MANAGER_DIR)/plugins.py \
		$(DOMOTICZ_PLUGINS_MANAGER_DIR)/README.md \
		$(DOMOTICZ_PLUGINS_MANAGER_DIR)/LICENSE \
		$(DOMOTICZ_PLUGINS_MANAGER_PLUGIN_DIR)/
	cp -r \
		$(DOMOTICZ_PLUGINS_MANAGER_DIR)/api/ \
		$(DOMOTICZ_PLUGINS_MANAGER_DIR)/frontend/ \
		$(DOMOTICZ_PLUGINS_MANAGER_PLUGIN_DIR)/
# Only the files are made world readable: chmod on a glob would clear the execute
# bit of the resource directories, which Python needs to traverse them.
	find $(DOMOTICZ_PLUGINS_MANAGER_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_PLUGINS_MANAGER_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
