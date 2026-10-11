$(call PKG_INIT_LIB, 0.8.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=soapy-sdr-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=a508083875ed75d1090c24f88abef9895ad65f0f1b54e96d74094478f0c400e6
$(PKG)_SITE:=https://github.com/pothosware/SoapySDR/archive/refs/tags
### VERSION:=0.8.1
### WEBSITE:=https://github.com/pothosware/SoapySDR
### CHANGES:=https://github.com/pothosware/SoapySDR/blob/master/CHANGELOG.md
### CVSREPO:=https://github.com/pothosware/SoapySDR

$(PKG)_CATEGORY_LIBS:=USB & related

# Upstream installs libSoapySDR.so.0.8.1 (SOAPY_SDR_LIBVER) and links against
# it through the SONAME libSoapySDR.so.0.8 (SOAPY_SDR_ABI_VERSION).
$(PKG)_LIB_VERSION:=$($(PKG)_VERSION)
$(PKG)_LIBNAME:=libSoapySDR.so.$($(PKG)_LIB_VERSION)
$(PKG)_BINARY:=$($(PKG)_DIR)/lib/$($(PKG)_LIBNAME)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/$($(PKG)_LIBNAME)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/$($(PKG)_LIBNAME)

$(PKG)_DEPENDS_ON += cmake-host

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_PROCESSOR=$(FREETZ_TARGET_ARCH)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY

# SoapySDR 0.8.1 still declares "cmake_minimum_required(VERSION 3.1.0)".
# CMake 4.x refuses to configure such projects unless this escape hatch is used.
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5

# Only the runtime library is needed: no SoapySDRUtil, no unit tests and no
# SWIG based Python bindings (they would need a target Python as well).
$(PKG)_CONFIGURE_OPTIONS += -DENABLE_APPS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DENABLE_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DENABLE_PYTHON=OFF
$(PKG)_CONFIGURE_OPTIONS += -DENABLE_PYTHON3=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(SOAPYSDR_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(SOAPYSDR_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(SOAPYSDR_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/SoapySDR \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libSoapySDR.so* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/SoapySDR.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/cmake/SoapySDR

$(pkg)-uninstall:
	$(RM) $(SOAPYSDR_TARGET_DIR)/libSoapySDR.so*

$(PKG_FINISH)
