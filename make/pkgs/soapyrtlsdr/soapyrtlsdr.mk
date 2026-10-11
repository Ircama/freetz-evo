$(call PKG_INIT_BIN, 0.3.3)
### STEWARD:=Ircama
$(PKG)_SOURCE_DOWNLOAD_NAME:=soapy-rtl-sdr-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=757c3c3bd17c5a12c7168db2f2f0fd274457e65f35e23c5ec9aec34e3ef54ece
$(PKG)_SITE:=https://github.com/pothosware/SoapyRTLSDR/archive/refs/tags
### WEBSITE:=https://github.com/pothosware/SoapyRTLSDR
### CHANGES:=https://github.com/pothosware/SoapyRTLSDR/blob/master/CHANGELOG.TXT
### CVSREPO:=https://github.com/pothosware/SoapyRTLSDR

# SoapySDR loads its hardware modules from <SOAPY_SDR_ROOT>/lib/SoapySDR/modules<abi>.
# SOAPY_SDR_ROOT is baked into libSoapySDR at build time and is "/usr" here.
# Upstream's CMake target is called "rtlsdrSupport", so the shared object is
# built as librtlsdrSupport.so; it is installed under the conventional module
# name (SoapySDR scans the directory and does not care about file names).
$(PKG)_BUILD_NAME:=librtlsdrSupport.so
$(PKG)_MODULE_NAME:=libsoapyrtlsdr.so
$(PKG)_MODULE_PATH:=/usr/lib/SoapySDR/modules0.8
$(PKG)_BINARY:=$($(PKG)_DIR)/$($(PKG)_BUILD_NAME)
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$($(PKG)_MODULE_PATH)/$($(PKG)_MODULE_NAME)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += soapysdr
$(PKG)_DEPENDS_ON += rtl-sdr

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libsoapysdr
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_rtl_sdr

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_PROCESSOR=$(FREETZ_TARGET_ARCH)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY

# 0.3.3 declares cmake_minimum_required(VERSION 2.8.7), which freetz' CMake 4.x
# refuses to configure without this escape hatch.
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5

# SoapySDR is found through the CMake package config installed by the soapysdr
# package, librtlsdr through SoapyRTLSDR's own FindRTLSDR.cmake.
$(PKG)_CONFIGURE_OPTIONS += -DSoapySDR_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/cmake/SoapySDR"
$(PKG)_CONFIGURE_OPTIONS += -DRTLSDR_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_OPTIONS += -DRTLSDR_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/librtlsdr.so"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(SOAPYRTLSDR_DIR)

# The module is dlopen()ed by absolute path, so a plain copy (no SONAME
# symlinks) into the SoapySDR module directory is all that is needed.
$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(SOAPYRTLSDR_DIR) clean
	$(RM) $(SOAPYRTLSDR_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(SOAPYRTLSDR_TARGET_BINARY)

$(PKG_FINISH)
