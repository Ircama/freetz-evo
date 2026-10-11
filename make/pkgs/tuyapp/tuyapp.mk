# tuyapp has no upstream releases yet, so we pin the source to a master
# commit (VERSION is the full commit hash, as done by esp-serial-flasher).
#
# Upstream builds a static library (libtuyapp.a) plus one executable per
# example in examples/. Its CMakeLists.txt lives in examples/ and finds
# jsoncpp through pkg-config, OpenSSL through find_package(OpenSSL).
$(call PKG_INIT_BIN, 5a3a462f62f1008bb7f220d98e8e47f84f7ae75a)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=1b99e142418644f9370f17157da82af7136105d196c3d243750e80c0ed2ea6ba
$(PKG)_SITE:=https://github.com/gordonb3/tuyapp/archive
### VERSION:=git-5a3a462
### WEBSITE:=https://github.com/gordonb3/tuyapp
### CHANGES:=https://github.com/gordonb3/tuyapp/commits/master
### CVSREPO:=https://github.com/gordonb3/tuyapp

# Clients built by upstream "make examples"
$(PKG)_TOOLS_LIST:=tuya_switch tuya_kwh_meter tuya_status tuya_multi_kwh_meter tuya_monitor_and_control
$(PKG)_TOOLS_BUILD:=$($(PKG)_TOOLS_LIST:%=$($(PKG)_DIR)/%)
$(PKG)_TOOLS_TARGET:=$($(PKG)_TOOLS_LIST:%=$($(PKG)_DEST_DIR)/usr/bin/%)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += jsoncpp
$(PKG)_DEPENDS_ON += openssl

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libjsoncpp
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libcrypto
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libssl

# The CMake project lives in examples/ and its output directories are
# derived from CMAKE_SOURCE_DIR, so it must be configured from within
# examples/ (this is exactly what upstream's "cmake -B examples -S examples"
# does).
$(PKG)_BUILD_SUBDIR:=examples

# Drop a possibly stale in-source CMake cache before re-configuring
$(PKG)_CONFIGURE_PRE_CMDS += $(RM) -r $($(PKG)_DIR)/examples/CMakeCache.txt $($(PKG)_DIR)/examples/CMakeFiles;

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_PROCESSOR=$(FREETZ_TARGET_ARCH)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_COMPILER="$(TARGET_CC)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_CXX_COMPILER="$(TARGET_CXX)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_AR="$(TARGET_AR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_RANLIB="$(TARGET_RANLIB)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_STRIP="$(TARGET_STRIP)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY

# Crypto backend: OpenSSL. The libraries are pinned explicitly so that the
# host OpenSSL can never be picked up by find_package(OpenSSL).
$(PKG)_CONFIGURE_OPTIONS += -DUSE_MBEDTLS=NO
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_ROOT_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_SSL_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libssl.so"
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_CRYPTO_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcrypto.so"

# Protocol support (upstream defaults: 3.1 off, 3.3/3.4/3.5 on)
$(PKG)_CONFIGURE_OPTIONS += -DWITHOUT_API31=YES
$(PKG)_CONFIGURE_OPTIONS += -DWITHOUT_API33=NO
$(PKG)_CONFIGURE_OPTIONS += -DWITHOUT_API34=NO
$(PKG)_CONFIGURE_OPTIONS += -DWITHOUT_API35=NO

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

# One CMake invocation builds the static library and all clients
$($(PKG)_DIR)/.built: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(TUYAPP_DIR)/examples
	@touch $@

# The client binaries are produced by the .built rule above (empty recipe so
# that make does not look for another rule for them)
$($(PKG)_TOOLS_BUILD): $($(PKG)_DIR)/.built ;

$($(PKG)_DEST_DIR)/usr/bin/tuya_switch: $($(PKG)_DIR)/tuya_switch
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/bin/tuya_kwh_meter: $($(PKG)_DIR)/tuya_kwh_meter
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/bin/tuya_status: $($(PKG)_DIR)/tuya_status
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/bin/tuya_multi_kwh_meter: $($(PKG)_DIR)/tuya_multi_kwh_meter
	$(INSTALL_BINARY_STRIP)

$($(PKG)_DEST_DIR)/usr/bin/tuya_monitor_and_control: $($(PKG)_DIR)/tuya_monitor_and_control
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TOOLS_TARGET)


$(pkg)-clean:
	-$(SUBMAKE) -C $(TUYAPP_DIR)/examples clean
	$(RM) -r $($(PKG)_DIR)/.lib $($(PKG)_DIR)/examples/CMakeCache.txt $($(PKG)_DIR)/examples/CMakeFiles $($(PKG)_DIR)/examples/Makefile $($(PKG)_DIR)/examples/cmake_install.cmake
	$(RM) $($(PKG)_TOOLS_BUILD) $($(PKG)_DIR)/.built $($(PKG)_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $($(PKG)_TOOLS_TARGET)

$(PKG_FINISH)
