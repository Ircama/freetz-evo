
### for PKGS+Tools

# Updates config.guess and config.sub for configure eg add aarch64.
#   $(1) = directories of config.* files to be updated
#
# The macro is intended to be used in $(PKG)_CONFIGURE_PRE_CMDS variable in the following way:
# $(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_UPDATE_CONFIGS,./)
# Don't forget to make sure config.* are available with:
# $(PKG)_DEPENDS_ON+=config-host
#
PKG_UPDATE_CONFIGS__INT = \
	cp -a -f $(FREETZ_BASE_DIR)/$(TOOLS_BUILD_DIR)/etc/config.{guess,sub} $1;
PKG_UPDATE_CONFIGS = $(foreach f,$1,$(call PKG_UPDATE_CONFIGS__INT,$(f)))


