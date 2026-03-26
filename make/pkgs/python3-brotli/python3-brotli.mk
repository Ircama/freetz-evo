$(call PKG_INIT_BIN, 1.1.0)
$(PKG)_SOURCE:=brotli-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=Brotli-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/B/Brotli
$(PKG)_HASH:=81de08ac11bcb85841e440c13611c00b67d3bf82698314928d0b676362546724
### WEBSITE:=https://github.com/google/brotli
### CHANGES:=https://github.com/google/brotli/releases
### CVSREPO:=https://github.com/google/brotli

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/brotli.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	@mkdir -p $(@D)
	@printf '%s\n' \
		'#!/bin/sh' \
		'args=""' \
		'for a in "$$@"; do' \
		'  case "$$a" in' \
		'    -I$(HOST_TOOLS_DIR)/usr/include/python$(PYTHON3_MAJOR_VERSION)) continue ;;' \
		'  esac' \
		'  q=$$(printf "%s" "$$a" | sed "s/'"'"'/\\'"'"''"'"'/g")' \
		'  args="$$args '\''$$q'\''"' \
		'done' \
		'eval "set -- $$args"' \
		'exec $(TARGET_CC) -I$(PYTHON3_STAGING_INC_DIR) "$$@"' \
	> $(abspath $(@D))/.cc-wrap.sh
	@chmod +x $(abspath $(@D))/.cc-wrap.sh
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) pkgconfig
	$(call Build/PyMod3/Pip, PYTHON3_BROTLI, , \
		CC="$(abspath $(@D))/.cc-wrap.sh" \
		CXX="$(TARGET_CXX)" \
		LDSHARED="$(abspath $(@D))/.cc-wrap.sh -shared" \
		BLDSHARED="$(abspath $(@D))/.cc-wrap.sh -shared" \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_BROTLI_DIR)/.configured
	$(RM) -r $(PYTHON3_BROTLI_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_BROTLI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/brotli.py \
		$(PYTHON3_BROTLI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/_brotli*.so \
		$(PYTHON3_BROTLI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/brotli-*.dist-info

$(PKG_FINISH)
