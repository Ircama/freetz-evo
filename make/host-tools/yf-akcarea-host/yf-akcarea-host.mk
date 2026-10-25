$(call TOOLS_INIT, 1.0)
### STEWARD:=EOL

$(PKG)_DEPENDS_ON+=sfk-host
$(PKG)_DEPENDS_ON+=dtc-host

$(PKG)_BINS:=extract bin2asm
$(PKG)_BUILD_DIR:=$($(PKG)_BINS:%=$($(PKG)_DIR)/avm_kernel_config.%)
$(PKG)_TARGET_DIR:=$($(PKG)_BINS:%=$(TOOLS_DIR)/avm_kernel_config.%)


$(TOOLS_LOCALSOURCE_PACKAGE)
$(TOOLS_CONFIGURED_NOP)

$($(PKG)_BUILD_DIR): $($(PKG)_DIR)/.unpacked
	$(TOOLS_SUBMAKE) -C $(YF_AKCAREA_HOST_DIR) \
		CC="$(TOOLS_CC)" \
		LIBFDT_DIR=$(DTC_HOST_INCLUDE_LIB) \
		$(YF_AKCAREA_HOST_BINS:%=avm_kernel_config.%)
	touch -c $@

$($(PKG)_TARGET_DIR): $(TOOLS_DIR)/avm_kernel_config.%: $($(PKG)_DIR)/avm_kernel_config.%
	$(INSTALL_FILE)

$(pkg)-precompiled: $($(PKG)_TARGET_DIR)


$(pkg)-clean:
	-$(MAKE) -C $(YF_AKCAREA_HOST_DIR) clean
	-$(RM) $(YF_AKCAREA_HOST_DIR)/.{configured,compiled}

$(pkg)-dirclean:
	$(RM) -r $(YF_AKCAREA_HOST_DIR)

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(YF_AKCAREA_HOST_TARGET_DIR)

$(TOOLS_FINISH)
