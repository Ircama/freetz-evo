$(call PKG_INIT_BIN, f882bce51f705c557b830717d9ea07d88ad86162)
# Upstream has no release tags, so the version is the commit of the default
# branch: the same convention as the other plugin packages in this tree.
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=304dc9e2dd97a37a92648d0f8f0e96bf0e89dad775546e9a42525af8e6b34cc2
$(PKG)_SITE:=https://github.com/CreasolTech/domoticz-dts238/archive
### WEBSITE:=https://github.com/CreasolTech/domoticz-dts238
### CHANGES:=https://github.com/CreasolTech/domoticz-dts238/commits
### CVSREPO:=https://github.com/CreasolTech/domoticz-dts238
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
$(PKG)_PLUGIN_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz/plugins/domoticz-dts238
$(PKG)_PLUGIN_STAMP:=$($(PKG)_PLUGIN_DIR)/plugin.py

$(PKG)_DEPENDS_ON += domoticz
$(PKG)_DEPENDS_ON += python3-pyserial
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_DOMOTICZ_DTS238

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# Everything the plugin needs at run time: the Python modules of the repository
# (`plugin.py` and the helpers it imports), the upstream documentation.
$($(PKG)_PLUGIN_STAMP): $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_DTS238_PLUGIN_DIR)
	cp \
		$(DOMOTICZ_DTS238_DIR)/minimalmodbus.py \
		$(DOMOTICZ_DTS238_DIR)/plugin.py \
		$(DOMOTICZ_DTS238_DIR)/README.md \
		$(DOMOTICZ_DTS238_DIR)/LICENSE \
		$(DOMOTICZ_DTS238_DIR)/ChangeLog \
		$(DOMOTICZ_DTS238_PLUGIN_DIR)/
# Only the files are made world readable: chmod on a glob would clear the execute
# bit of the resource directories, which Python needs to traverse them.
	find $(DOMOTICZ_DTS238_PLUGIN_DIR) -type f -exec chmod 644 {} \;

$(pkg): $($(PKG)_PLUGIN_STAMP)

$(pkg)-precompiled: $($(PKG)_PLUGIN_STAMP)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_DTS238_PLUGIN_DIR)

$(pkg)-uninstall: $(pkg)-clean

$(PKG_FINISH)
