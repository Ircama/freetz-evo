$(call PKG_INIT_BIN, $(if $(FREETZ_PACKAGE_PYTHON3_NUMPY_VERSION_ABANDON),2.3.2,2.4.3))
$(PKG)_SOURCE:=numpy-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=numpy-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/n/numpy
$(PKG)_HASH_ABANDON:=e0486a11ec30cdecb53f184d496d1c6a20786c81e55e41640270130056f8ee48
$(PKG)_HASH_CURRENT:=483a201202b73495f00dbc83796c6ae63137a9bdade074f7648b3e32613412dd
$(PKG)_HASH:=$($(PKG)_HASH_$(if $(FREETZ_PACKAGE_PYTHON3_NUMPY_VERSION_ABANDON),ABANDON,CURRENT))
### WEBSITE:=https://numpy.org/
### MANPAGE:=https://numpy.org/doc/stable/
### CHANGES:=https://numpy.org/doc/stable/release.html
### CVSREPO:=https://github.com/numpy/numpy
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += meson-host
$(PKG)_DEPENDS_ON += ninja-host
$(PKG)_DEPENDS_ON += openlibm

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_NUMPY_VERSION_ABANDON

PYTHON3_NUMPY_MESON_CROSS_FILE:=$(PYTHON3_NUMPY_DIR)/meson.freetz

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/numpy/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cat $(INCLUDE_DIR)/meson.cross/$(call qstrip,$(FREETZ_TARGET_UCLIBC_TRIPLET)) > $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	@sed \
		-e 's!%FREETZ_TARGET_UCLIBC_TRIPLET%!$(call qstrip,$(FREETZ_TARGET_UCLIBC_TRIPLET))!g' \
		-e 's!%FREETZ_TARGET_MESON_FAMILY%!$(call qstrip,$(FREETZ_TARGET_MESON_FAMILY))!' \
		-e 's!%FREETZ_TARGET_MESON_CPU%!$(call qstrip,$(FREETZ_TARGET_MESON_CPU))!' \
		-e 's!%FREETZ_TARGET_MESON_ENDIAN%!$(call qstrip,$(FREETZ_TARGET_MESON_ENDIAN))!' \
		-e 's!%FREETZ_TARGET_MESON_ENDIAN_UPPER%!$(call qstrip,$(FREETZ_TARGET_MESON_ENDIAN_UPPER))!' \
		-e "s!%TARGET_CFLAGS%!$(foreach X,$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR) -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/openlibm,'$(X)',)!g" \
		-e "s!%TARGET_LDFLAGS%!$(foreach X,$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR) -L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -lopenlibm,'$(X)',)!g" \
		-e 's!%TARGET_AR%!$(call qstrip,$(TARGET_AR))!g' \
		-e 's!%TARGET_AS%!$(call qstrip,$(TARGET_AS))!g' \
		-e 's!%TARGET_CC%!$(call qstrip,$(TARGET_CC))!g' \
		-e 's!%TARGET_CXX%!$(call qstrip,$(TARGET_CXX))!g' \
		-e 's!%TARGET_LD%!$(call qstrip,$(TARGET_LD))!g' \
		-e 's!%TARGET_LDCONFIG%!$(call qstrip,$(TARGET_LDCONFIG))!g' \
		-e 's!%TARGET_NM%!$(call qstrip,$(TARGET_NM))!g' \
		-e 's!%TARGET_RANLIB%!$(call qstrip,$(TARGET_RANLIB))!g' \
		-e 's!%TARGET_OBJCOPY%!$(call qstrip,$(TARGET_OBJCOPY))!g' \
		-e 's!%TARGET_READELF%!$(call qstrip,$(TARGET_READELF))!g' \
		-e 's!%TARGET_STRIP%!$(call qstrip,$(TARGET_STRIP))!g' \
		-e 's!%PKGCONFIG%!$(call qstrip,$(TARGET_MAKE_PATH))/../lib/pkgconfig!g' \
		-e 's!%PYTHON%!$(call qstrip,$(TOOLS_DIR))/path/cmake!g' \
		-e 's!%CMAKE%!$(call qstrip,$(TOOLS_DIR))/path/python3!g' \
		$(INCLUDE_DIR)/meson.cross/common-linux-uclibc >> $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	@sed -i \
		-e "s|^python[[:space:]]*=.*|python = '$(HOST_PYTHON3_BIN)'|" \
		-e "s|^pkgconfig[[:space:]]*=.*|pkg-config = 'pkg-config'|" \
		$(PYTHON3_NUMPY_MESON_CROSS_FILE)
	@printf "\n[host_machine]\n" >> $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	@printf "system = 'linux'\n" >> $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	@printf "cpu_family = '$(call qstrip,$(FREETZ_TARGET_MESON_FAMILY))'\n" >> $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	@printf "cpu = '$(call qstrip,$(FREETZ_TARGET_MESON_CPU))'\n" >> $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	@printf "endian = '$(call qstrip,$(FREETZ_TARGET_MESON_ENDIAN))'\n" >> $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	$(call Build/PyMod3/Pip, PYTHON3_NUMPY, \
		--config-settings=setup-args=--cross-file=$(abspath $(PYTHON3_NUMPY_MESON_CROSS_FILE)), \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR) -L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -lopenlibm" \
		LIBS="-lopenlibm" \
	, isolated, no-build-ext-config)
	@printf '%s\n' \
		"import io" \
		"import os" \
		"import re" \
		"import sys" \
		"" \
		"f = '$(PYTHON3_NUMPY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/numpy/_core/__init__.py'" \
		"if not os.path.exists(f):" \
		"    sys.exit('Freetz python3-numpy.mk: File not found: %s' % f)" \
		"" \
		"with io.open(f, 'r', encoding='utf-8') as fh:" \
		"    src = fh.read()" \
		"" \
		"if 'catch_warnings()' in src and 'overflow encountered in cast' in src:" \
		"    sys.exit(0)" \
		"" \
		"pattern = re.compile(r'^(\\s*)from\\s+\\.\\s+import\\s+multiarray\\s*$$', re.MULTILINE)" \
		"replacement = lambda m: (" \
		"    m.group(1) + 'import warnings as _numpy_w\\n' +" \
		"    m.group(1) + 'with _numpy_w.catch_warnings():\\n' +" \
		"    m.group(1) + '    _numpy_w.filterwarnings(\"ignore\", message=\"overflow encountered in cast\", category=RuntimeWarning)\\n' +" \
		"    m.group(1) + '    from . import multiarray'" \
		")" \
		"new_src, n = pattern.subn(replacement, src, count=1)" \
		"if n == 0:" \
		"    sys.exit('Freetz python3-numpy.mk: Pattern not found')" \
		"" \
		"with io.open(f, 'w', encoding='utf-8') as fh:" \
		"    fh.write(new_src)" \
	| $(TOOLS_DIR)/path/python3
	$(RM) -r $(PYTHON3_NUMPY_DIR)/build

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_NUMPY_DIR)/.configured
	$(RM) $(PYTHON3_NUMPY_MESON_CROSS_FILE)
	$(RM) -r $(PYTHON3_NUMPY_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_NUMPY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/numpy \
		$(PYTHON3_NUMPY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/numpy-*.dist-info

$(PKG_FINISH)
