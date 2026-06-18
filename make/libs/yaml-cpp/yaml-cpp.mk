$(call PKG_INIT_LIB, 0.8.0)
$(PKG)_LIB_VERSION:=0.8.0
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=fbe74bbdcee21d656715688706da3c8becfd946d92cd44705cc6098bb23b3a16
$(PKG)_SITE:=https://github.com/jbeder/yaml-cpp/archive/refs/tags
### WEBSITE:=https://github.com/jbeder/yaml-cpp
### CHANGES:=https://github.com/jbeder/yaml-cpp/releases
### CVSREPO:=https://github.com/jbeder/yaml-cpp

$(PKG)_BINARY:=$($(PKG)_DIR)/libyaml-cpp.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libyaml-cpp.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libyaml-cpp.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DYAML_BUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DYAML_CPP_BUILD_TOOLS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DYAML_CPP_BUILD_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DYAML_CPP_INSTALL=ON


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(YAML_CPP_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(YAML_CPP_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

# Ensure yaml-cpp.pc exists even if staging binary is up-to-date
$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/yaml-cpp.pc:
	@mkdir -p $(dir $@)
	echo -ne \
		"prefix=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr\n"\
		"exec_prefix=\$${prefix}\n"\
		"libdir=\$${prefix}/lib\n"\
		"includedir=\$${prefix}/include\n"\
		"\n"\
		"Name: yaml-cpp\n"\
		"Description: YAML parser and emitter for C++\n"\
		"Version: $(YAML_CPP_VERSION)\n"\
		"Requires:\n"\
		"Libs: -L\$${libdir} -lyaml-cpp\n"\
		"Cflags: -I\$${includedir}\n"\
		>$@

$(pkg): $($(PKG)_STAGING_BINARY) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/yaml-cpp.pc

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(YAML_CPP_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libyaml-cpp.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/yaml-cpp.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/cmake/yaml-cpp/ \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/yaml-cpp/

$(pkg)-uninstall:
	$(RM) $(YAML_CPP_TARGET_DIR)/libyaml-cpp.so*

$(PKG_FINISH)