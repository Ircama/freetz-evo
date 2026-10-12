# Upstream has no usable release (only an ancient 0.0.1 tag), so pin "main".
$(call PKG_INIT_BIN, 0208badefb2003d30e70b5b875395e3187c850d9)
### STEWARD:=Ircama
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=70e0d99d13d8e1cbef40623dfb8c216ce4285f7fe885af1129f626ae2f00f79d
$(PKG)_SITE:=https://github.com/tuya/tuya-iot-core-sdk/archive
### VERSION:=git-0208bad
### WEBSITE:=https://github.com/tuya/tuya-iot-core-sdk
### CHANGES:=https://github.com/tuya/tuya-iot-core-sdk/commits/main
### CVSREPO:=https://github.com/tuya/tuya-iot-core-sdk

$(PKG)_CATEGORY_PKGS:=Home Automation

# Upstream explicitly refuses in-source builds, so configure and build in
# "build/" and install the demo programs by hand (the project has no install
# rules; the SDK itself is linked statically into the demos).
$(PKG)_BUILD_DIR:=$($(PKG)_DIR)/build

$(PKG)_DEMOS:=custom_protocol_basic_demo data_model_basic_demo ota_basic_demo subdevice_basic_demo
$(PKG)_DEMOS_BUILD:=$($(PKG)_DEMOS:%=$($(PKG)_BUILD_DIR)/bin/%)
$(PKG)_DEMOS_TARGET:=$($(PKG)_DEMOS:%=$($(PKG)_DEST_DIR)/usr/bin/%)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_STRIP="$(TARGET_STRIP)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_PROCESSOR=$(FREETZ_TARGET_ARCH)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY

# Upstream declares cmake_minimum_required(VERSION 3.2.0), which freetz'
# CMake 4.x refuses to configure without this escape hatch.
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5

# mbedTLS, coreJSON, coreMQTT and coreHTTP are vendored in the tarball (as git
# sub-trees, not submodules) and the demo CA certificate is embedded in the
# demo sources, so neither submodules nor certificates may be fetched.
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_CLONE_SUBMODULES=OFF
$(PKG)_CONFIGURE_OPTIONS += -DDOWNLOAD_CERTS=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.build-prereq-checked $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	$(RM) -r $(TUYA_IOT_CORE_SDK_BUILD_DIR)
	mkdir -p $(TUYA_IOT_CORE_SDK_BUILD_DIR)
	cd $(TUYA_IOT_CORE_SDK_BUILD_DIR); \
		$(MAKE_ENV) $(TARGET_CONFIGURE_ENV) \
		$(CMAKE) .. \
		$(TUYA_IOT_CORE_SDK_CONFIGURE_OPTIONS)
	@touch $@

$($(PKG)_DIR)/.built: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TUYA_IOT_CORE_SDK_BUILD_DIR)
	@touch $@

# The demo binaries are produced by the .built rule above (empty recipe so that
# make does not look for another rule for them)
$($(PKG)_DEMOS_BUILD): $($(PKG)_DIR)/.built ;

$($(PKG)_DEMOS_TARGET): $($(PKG)_DEST_DIR)/usr/bin/%: $($(PKG)_BUILD_DIR)/bin/%
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_DEMOS_TARGET)


$(pkg)-clean:
	-$(SUBMAKE) -C $(TUYA_IOT_CORE_SDK_BUILD_DIR) clean
	$(RM) -r $(TUYA_IOT_CORE_SDK_BUILD_DIR) $(TUYA_IOT_CORE_SDK_DIR)/.configured $(TUYA_IOT_CORE_SDK_DIR)/.built

$(pkg)-uninstall:
	$(RM) $(TUYA_IOT_CORE_SDK_DEMOS_TARGET)

$(PKG_FINISH)
