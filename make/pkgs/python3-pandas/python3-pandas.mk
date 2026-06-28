$(call PKG_INIT_BIN, $(if $(FREETZ_PACKAGE_PYTHON3_PANDAS_VERSION_ABANDON),2.3.3,$(if $(FREETZ_PACKAGE_PYTHON3_PANDAS_VERSION_OLD),3.0.1,3.0.3)))
$(PKG)_SOURCE:=pandas-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pandas-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pandas
$(PKG)_HASH_ABANDON:=e05e1af93b977f7eafa636d043f9f94c7ee3ac81af99c13508215942e64c993b
$(PKG)_HASH_OLD:=4186a699674af418f655dbd420ed87f50d56b4cd6603784279d9eef6627823c8
$(PKG)_HASH_CURRENT:=696a4a00a2a2a35d4e5deb3fc946641b96c944f02230e4f76137fe35d806c4fc
$(PKG)_HASH:=$($(PKG)_HASH_$(if $(FREETZ_PACKAGE_PYTHON3_PANDAS_VERSION_ABANDON),ABANDON,$(if $(FREETZ_PACKAGE_PYTHON3_PANDAS_VERSION_OLD),OLD,CURRENT)))
### WEBSITE:=https://pandas.pydata.org/
### MANPAGE:=https://pandas.pydata.org/docs/
### CHANGES:=https://pandas.pydata.org/docs/whatsnew/
### CVSREPO:=https://github.com/pandas-dev/pandas
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += meson-host
$(PKG)_DEPENDS_ON += ninja-host
$(PKG)_DEPENDS_ON += python3-numpy

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_PANDAS_VERSION_ABANDON
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_PANDAS_VERSION_OLD
$(PKG)_DEPENDS_ON += python3-dateutil

PYTHON3_PANDAS_MESON_CROSS_FILE:=$(PYTHON3_PANDAS_DIR)/meson.freetz

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pandas/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cat $(INCLUDE_DIR)/meson.cross/$(call qstrip,$(FREETZ_TARGET_UCLIBC_TRIPLET)) > $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@sed \
		-e 's!%FREETZ_TARGET_UCLIBC_TRIPLET%!$(call qstrip,$(FREETZ_TARGET_UCLIBC_TRIPLET))!g' \
		-e 's!%FREETZ_TARGET_MESON_FAMILY%!$(call qstrip,$(FREETZ_TARGET_MESON_FAMILY))!' \
		-e 's!%FREETZ_TARGET_MESON_CPU%!$(call qstrip,$(FREETZ_TARGET_MESON_CPU))!' \
		-e 's!%FREETZ_TARGET_MESON_ENDIAN%!$(call qstrip,$(FREETZ_TARGET_MESON_ENDIAN))!' \
		-e 's!%FREETZ_TARGET_MESON_ENDIAN_UPPER%!$(call qstrip,$(FREETZ_TARGET_MESON_ENDIAN_UPPER))!' \
		-e "s!%TARGET_CFLAGS%!$(foreach X,$(TARGET_CFLAGS),'$(X)',)!g" \
		-e "s!%TARGET_LDFLAGS%!$(foreach X,$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR),'$(X)',)!g" \
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
		$(INCLUDE_DIR)/meson.cross/common-linux-uclibc >> $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@sed -i \
		-e "s|^python[[:space:]]*=.*|python = '$(HOST_PYTHON3_BIN)'|" \
		-e "s|^pkgconfig[[:space:]]*=.*|pkg-config = 'pkg-config'|" \
		$(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@printf "\n[host_machine]\n" >> $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@printf "system = 'linux'\n" >> $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@printf "cpu_family = '$(call qstrip,$(FREETZ_TARGET_MESON_FAMILY))'\n" >> $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@printf "cpu = '$(call qstrip,$(FREETZ_TARGET_MESON_CPU))'\n" >> $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@printf "endian = '$(call qstrip,$(FREETZ_TARGET_MESON_ENDIAN))'\n" >> $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	@if [ "$(FREETZ_PACKAGE_PYTHON3_PANDAS_VERSION_ABANDON)" != "y" ]; then \
		sed -i 's/NPY_1_21_API_VERSION/NPY_2_0_API_VERSION/g' $(PYTHON3_PANDAS_DIR)/meson.build 2>/dev/null || true; \
		$(TOOLS_DIR)/path/python3 "$(abspath $(dir $(lastword $(MAKEFILE_LIST))))/patches/110-add-compat-macros.py" \
			"$(PYTHON3_PANDAS_DIR)/meson.build" 2>/dev/null || true; \
	fi
	$(call Build/PyMod3/Pip, PYTHON3_PANDAS, \
		--config-settings=setup-args=--cross-file=$(abspath $(PYTHON3_PANDAS_MESON_CROSS_FILE)), \
		PANDAS_NUMPY_INCLUDE_DIR="$(abspath $(PYTHON3_NUMPY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/numpy/_core/include)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	, isolated, no-build-ext-config)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PANDAS_DIR)/.configured
	$(RM) $(PYTHON3_PANDAS_MESON_CROSS_FILE)
	$(RM) -r $(PYTHON3_PANDAS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PANDAS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pandas \
		$(PYTHON3_PANDAS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pandas-*.dist-info

$(PKG_FINISH)
