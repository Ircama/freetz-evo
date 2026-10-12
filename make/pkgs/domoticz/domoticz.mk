# Domoticz 2026.4 - C++17 home automation system (CMake based).
#
# Notes:
#  - GitHub source archives never contain submodule contents, but Domoticz's
#    CMakeLists.txt adds extern/{jsoncpp,minizip,jwtcpp,libwebem} to the build
#    unconditionally. The exact commits referenced by the 2026.4 tag are
#    downloaded as separate tarballs and unpacked into extern/ before
#    configure runs; -DGIT_SUBMODULE=OFF keeps CMake from invoking git.
#  - Boost comes from the tree's boost package (b2 cross build) together with
#    a BoostConfig.cmake, because CMake 4.x dropped the FindBoost module.
#  - SQLite is linked from the tree's sqlite package (USE_BUILTIN_SQLITE=NO).
#  - Python plugin support is enabled and links the target libpython3.14
#    (FREETZ_LIB_libpython3); Tellus/OpenZWave support is unavailable.
#  - The Domoticz updater is disabled (it would download host binaries).
$(call PKG_INIT_BIN, 2026.4)
### STEWARD:=Ircama

$(PKG)_CATEGORY_PKGS:=Home Automation

$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=9cc0deff15cc1466d1c006295f0af253681ff844a2d70d8fad511082a9cce66e
$(PKG)_SITE:=https://github.com/domoticz/domoticz/archive/refs/tags
### WEBSITE:=https://www.domoticz.com/
### CHANGES:=https://github.com/domoticz/domoticz/blob/development/History.txt
### CVSREPO:=https://github.com/domoticz/domoticz

$(PKG)_BUILD_DIR:=$($(PKG)_DIR)/freetz-build
$(PKG)_BINARY:=$($(PKG)_BUILD_DIR)/domoticz
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/domoticz

# --------------------------------------------------------------------------
# Submodule sources (commits referenced by the 2026.4 tag, from .gitmodules
# plus the GitHub tree API for that tag)
# --------------------------------------------------------------------------
$(PKG)_SUBMODULES:=jsoncpp jwtcpp libwebem minizip

$(PKG)_SUB_jsoncpp_SITE:=https://github.com/open-source-parsers/jsoncpp/archive
$(PKG)_SUB_jsoncpp_COMMIT:=89e2973c754a9c02a49974d839779b151e95afd6
$(PKG)_SUB_jsoncpp_HASH:=fbdcd9beff428968710f339b15ae3911e295a5a71da0cbadbdd631d7a5aeaaee

$(PKG)_SUB_jwtcpp_SITE:=https://github.com/Thalhammer/jwt-cpp/archive
$(PKG)_SUB_jwtcpp_COMMIT:=3e037df3e669633a3044618e30550ea2f212e915
$(PKG)_SUB_jwtcpp_HASH:=e42e4b146752038edd72474dc5244c5ba2fbfcd1c87c63a7f2beed90d175f452

$(PKG)_SUB_libwebem_SITE:=https://github.com/domoticz/libwebem/archive
$(PKG)_SUB_libwebem_COMMIT:=dde28f230efefa279aceb92f039ea251b34234d8
$(PKG)_SUB_libwebem_HASH:=0b22316f42c658bfc56bb2007310b1bf52063bc8d41aea9789ee301441c45f01

$(PKG)_SUB_minizip_SITE:=https://github.com/domoticz/minizip/archive
$(PKG)_SUB_minizip_COMMIT:=aee7fbddf118d9363575af96310c29fa747d70c0
$(PKG)_SUB_minizip_HASH:=c460edc8df08bd13a883d7cef939756d9926ec130c259b3e3d56d5ff8d500858

# $1: submodule name
# Note: the rule targets are spelled out instead of using variables that are
# assigned within the same $(call) expansion - those would still be empty while
# the body is being expanded (the assignments only take effect when $(eval)
# parses the result).
define DOMOTICZ_SUBMODULE_RULES
$(PKG)_SUB_$(1)_MARKER:=$($(PKG)_DIR)/extern/.$(1)-unpacked
$(PKG)_SUB_$(1)_DL:=$(DL_DIR)/$(pkg)-sub-$(1)-$($(PKG)_SUB_$(1)_COMMIT).tar.gz

$(DL_DIR)/$(pkg)-sub-$(1)-$($(PKG)_SUB_$(1)_COMMIT).tar.gz: | $(DL_DIR)
	$(DL_TOOL) -o $(pkg)-sub-$(1)-$($(PKG)_SUB_$(1)_COMMIT).tar.gz $(DL_DIR) \
		$($(PKG)_SUB_$(1)_COMMIT).tar.gz $($(PKG)_SUB_$(1)_SITE) $($(PKG)_SUB_$(1)_HASH)

$($(PKG)_DIR)/extern/.$(1)-unpacked: $(DL_DIR)/$(pkg)-sub-$(1)-$($(PKG)_SUB_$(1)_COMMIT).tar.gz $($(PKG)_DIR)/.unpacked
	$(RM) -r $($(PKG)_DIR)/extern/$(1)
	mkdir -p $($(PKG)_DIR)/extern/$(1)
	$(call UNPACK_TARBALL,$(DL_DIR)/$(pkg)-sub-$(1)-$($(PKG)_SUB_$(1)_COMMIT).tar.gz,$($(PKG)_DIR)/extern/$(1),1)
	@touch $$@
endef

$(foreach submodule,$($(PKG)_SUBMODULES),$(eval $(call DOMOTICZ_SUBMODULE_RULES,$(submodule))))

$(PKG)_SUBMODULES_MARKERS:=$(foreach submodule,$($(PKG)_SUBMODULES),$($(PKG)_SUB_$(submodule)_MARKER))
$(PKG)_SUBMODULES_DONE:=$($(PKG)_DIR)/.submodules

$($(PKG)_SUBMODULES_DONE): $($(PKG)_SUBMODULES_MARKERS)
	@touch $@

# --------------------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------------------
$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += boost
$(PKG)_DEPENDS_ON += zlib
$(PKG)_DEPENDS_ON += curl
$(PKG)_DEPENDS_ON += openssl
$(PKG)_DEPENDS_ON += sqlite
$(PKG)_DEPENDS_ON += lua
$(PKG)_DEPENDS_ON += mosquitto
$(PKG)_DEPENDS_ON += libusb1
$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)

$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libboost_thread
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MOSQUITTO_CLIENTS
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libsqlite3
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_liblua

# --------------------------------------------------------------------------
# Configure
# --------------------------------------------------------------------------
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_PROCESSOR=$(FREETZ_TARGET_ARCH)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY

# Do not let CMake call git submodule (the submodules are unpacked above).
$(PKG)_CONFIGURE_OPTIONS += -DGIT_SUBMODULE=OFF
$(PKG)_CONFIGURE_OPTIONS += -DDISABLE_UPDATER=YES

# Bundled libraries: jsoncpp, minizip and jwt-cpp are unpacked as submodules,
# SQLite comes from the tree (Makefile.in installs a shared library).
$(PKG)_CONFIGURE_OPTIONS += -DUSE_BUILTIN_JSONCPP=YES
$(PKG)_CONFIGURE_OPTIONS += -DUSE_BUILTIN_MINIZIP=YES
$(PKG)_CONFIGURE_OPTIONS += -DUSE_BUILTIN_JWTCPP=YES
$(PKG)_CONFIGURE_OPTIONS += -DUSE_BUILTIN_SQLITE=NO

# Link Boost/libstdc++ dynamically (freetz ships both in the image).
$(PKG)_CONFIGURE_OPTIONS += -DUSE_STATIC_BOOST=OFF
$(PKG)_CONFIGURE_OPTIONS += -DUSE_STATIC_LIBSTDCXX=NO
$(PKG)_CONFIGURE_OPTIONS += -DUSE_STATIC_OPENZWAVE=NO

# Feature switches: Python plugins on, Tellus off, I2C/SPI auto-detected.
$(PKG)_CONFIGURE_OPTIONS += -DUSE_PYTHON=YES
$(PKG)_CONFIGURE_OPTIONS += -DWITH_TELLDUSCORE=NO
$(PKG)_CONFIGURE_OPTIONS += -DWITH_LIBUSB=YES
$(PKG)_CONFIGURE_OPTIONS += -DINCLUDE_LINUX_I2C=YES
$(PKG)_CONFIGURE_OPTIONS += -DINCLUDE_SPI=YES
$(PKG)_CONFIGURE_OPTIONS += -DUSE_PRECOMPILED_HEADER=YES

# Python3: the host interpreter built by the python3 package (3.14, same
# version as the target library) plus the target staging prefix, so that
# FindPython3 cannot pick up host headers/libraries.
$(PKG)_HOST_PYTHON3:=$(if $(HOST_TOOLS_DIR),$(HOST_TOOLS_DIR)/usr/bin/python3,$(TOOLS_DIR)/build/usr/bin/python3)
$(PKG)_CONFIGURE_OPTIONS += -DPython3_EXECUTABLE="$($(PKG)_HOST_PYTHON3)"
$(PKG)_CONFIGURE_OPTIONS += -DPython3_ROOT_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"
$(PKG)_CONFIGURE_OPTIONS += -DPython3_FIND_STRATEGY=LOCATION
$(PKG)_CONFIGURE_OPTIONS += -DPython3_FIND_IMPLEMENTATIONS=CPython

# Lua: the tree ships 5.4 with the headers in usr/include/lua, while upstream
# only searches for lua5.3 names and then adds ${LUA_INCLUDE_DIRS}/lua5.3 to
# the include path. Passing the values plus an explicit -I makes both work.
$(PKG)_CONFIGURE_OPTIONS += -DLUA_LIBRARIES="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblua.so"
$(PKG)_CONFIGURE_OPTIONS += -DLUA_INCLUDE_DIRS="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/lua"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_FLAGS="$(TARGET_CFLAGS) -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/lua"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_CXX_FLAGS="$(TARGET_CFLAGS) -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/lua"

# Mosquitto (mandatory upstream dependency).
$(PKG)_CONFIGURE_OPTIONS += -DMQTT_LIBRARIES="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmosquitto.so"
$(PKG)_CONFIGURE_OPTIONS += -DMQTT_INCLUDE_DIRS="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"

# libpython3 and libcurl list libatomic.so.1 in their DT_NEEDED entries, so the
# DSO has to be named on the link line (ld defaults to
# --no-copy-dt-needed-entries). Same workaround as ffmpeg/cmus/openssl.
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_EXE_LINKER_FLAGS="-latomic"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.build-prereq-checked $($(PKG)_DIR)/.unpacked $($(PKG)_SUBMODULES_DONE) $(DOMOTICZ_MAKE_DIR)/$(pkg).mk
	@$(call _ECHO,configuring)
	$(RM) -r $(DOMOTICZ_BUILD_DIR)
	mkdir -p $(DOMOTICZ_BUILD_DIR)
	cd $(DOMOTICZ_BUILD_DIR); \
		$(MAKE_ENV) $(TARGET_CONFIGURE_ENV) \
		$(CMAKE) .. \
		$(DOMOTICZ_CONFIGURE_OPTIONS)
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(DOMOTICZ_BUILD_DIR)

# --------------------------------------------------------------------------
# Install
# --------------------------------------------------------------------------
$(PKG)_DATA_DIR:=$($(PKG)_DEST_DIR)/usr/share/domoticz
$(PKG)_DATA_FILES:=History.txt License.txt server_cert.pem
$(PKG)_DATA_DIRS:=www dzVents plugins scripts
$(PKG)_DATA_TARGETS:=$(foreach file,$($(PKG)_DATA_FILES),$($(PKG)_DATA_DIR)/$(file)) \
	$(foreach dir,$($(PKG)_DATA_DIRS),$($(PKG)_DATA_DIR)/$(dir))

# Runtime integration: init script and the configuration of the freetz
# configuration framework (/etc/default.domoticz/domoticz.cfg is linked into
# /mod/etc/default.domoticz by the mod package, the saved values end up in
# /mod/etc/conf/domoticz.cfg).
$(PKG)_STAGING_SOURCES := \
	$(DOMOTICZ_MAKE_DIR)/files/.language \
	$(DOMOTICZ_MAKE_DIR)/files/root/etc/default.domoticz/domoticz.cfg \
	$(DOMOTICZ_MAKE_DIR)/files/root/etc/default.domoticz/domoticz.save \
	$(DOMOTICZ_MAKE_DIR)/files/root/etc/init.d/rc.domoticz \
	$(DOMOTICZ_MAKE_DIR)/files/root/usr/lib/cgi-bin/domoticz.cgi
$(PKG)_STAGING_TARGET := $($(PKG)_DEST_DIR)/etc/init.d/rc.domoticz

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(DOMOTICZ_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(DOMOTICZ_MAKE_DIR)/files,$(DOMOTICZ_TARGET_DIR))
	chmod 755 \
		$(DOMOTICZ_DEST_DIR)/etc/init.d/rc.domoticz \
		$(DOMOTICZ_DEST_DIR)/etc/default.domoticz/domoticz.save \
		$(DOMOTICZ_DEST_DIR)/usr/lib/cgi-bin/domoticz.cgi

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

# $* is the name of the file or directory to copy (History.txt, www, dzVents,
# plugins, scripts, ...). The rule only depends on the unpacked stamp, because
# the sources do not exist yet when make parses the package.
$($(PKG)_DATA_DIR)/%: $($(PKG)_DIR)/.unpacked
	mkdir -p $(DOMOTICZ_DATA_DIR)
	cp -a $(DOMOTICZ_DIR)/$* $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_DATA_TARGETS) $($(PKG)_STAGING_TARGET)

$(pkg)-clean:
	$(RM) -r $(DOMOTICZ_BUILD_DIR) $(DOMOTICZ_DIR)/.configured $(DOMOTICZ_SUBMODULES_MARKERS) $(DOMOTICZ_SUBMODULES_DONE)

$(pkg)-uninstall:
	$(RM) -r $(DOMOTICZ_TARGET_BINARY) $(DOMOTICZ_DATA_DIR)

$(PKG_FINISH)
