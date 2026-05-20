$(call PKG_INIT_BIN, 1.0)

$(PKG)_CATEGORY:=Audio

$(PKG)_TARGET_PLUGIN := $($(PKG)_DEST_DIR)$(FREETZ_LIBRARY_DIR)/ladspa/caps.so
$(PKG)_TARGET_RDF := $($(PKG)_DEST_DIR)/usr/share/ladspa/rdf/caps.rdf

$($(PKG)_TARGET_PLUGIN): $(CAPS_STAGING_BINARY) | $(PACKAGES_DIR)
	mkdir -p $(dir $@)
	cp -a $< $@
	$(TARGET_STRIP) $@ 2>/dev/null || true

$($(PKG)_TARGET_RDF): $(CAPS_STAGING_RDF) | $(PACKAGES_DIR)
	mkdir -p $(dir $@)
	cp -a $< $@

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_TARGET_PLUGIN) $($(PKG)_TARGET_RDF)

$(pkg)-clean:

$(pkg)-uninstall:
	$(RM) -f $($(PKG)_TARGET_PLUGIN) $($(PKG)_TARGET_RDF)

$(PKG_FINISH)