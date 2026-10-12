$(call PKG_INIT_BIN, 1.0)
$(PKG)_CATEGORY_PKGS:=Home Automation
$(PKG)_DEPENDS_ON += python3

$(PKG_UNPACKED)

# Files-only package: everything of value lives in files/root and is copied by
# the framework. The actual Python payload (Home Assistant plus its countless
# dependencies) is installed on demand by /usr/bin/ha-setup into the external
# base directory, because it cannot be cross-compiled here.

$(pkg):

$(pkg)-precompiled:

$(pkg)-clean:

$(PKG_FINISH)
