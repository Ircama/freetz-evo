# OpenThread v2026.10.0 -- open source implementation of the Thread protocol.
#
# Built for the POSIX platform, which provides the Thread daemon and its
# control client:
#   ot-daemon   Thread stack as a daemon
#   ot-ctl      control client (full CLI command set, talks to ot-daemon)
# Upstream selects the POSIX application as either/or: OT_APP_DAEMON (used
# here) or OT_APP_CLI for a standalone CLI.
# The 802.15.4 radio itself is not part of this package: an 802.15.4 SoC (for
# example an nRF52840 dongle) has to run the OpenThread RCP firmware and is
# reached through spinel over UART or a unix socket.
#
# third_party/mbedtls/repo is the only git submodule of the 2026.10.0 tag and
# GitHub source archives never contain submodule contents, so the pinned mbedTLS
# commit is downloaded as an extra tarball and unpacked into place before
# configure runs. third_party/tcplp is vendored in the archive.
#
# Note: OpenThread 2026 needs a C++11 capable toolchain, therefore the package
# is limited to uClibc >= 1.0.58 (GCC 13.4 in this tree).
$(call PKG_INIT_BIN, 2026.10.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Home Automation

$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=e92b3e420e23371b11869bbdb5da4c5b2adafaf92c0c5e374c462eba669ce292
$(PKG)_SITE:=https://github.com/openthread/openthread/archive/refs/tags
### WEBSITE:=https://openthread.io/
### CHANGES:=https://github.com/openthread/openthread/releases
### CVSREPO:=https://github.com/openthread/openthread

# --------------------------------------------------------------------------
# mbedTLS submodule pinned by the 2026.10.0 tag (third_party/mbedtls/repo)
# --------------------------------------------------------------------------
$(PKG)_MBEDTLS_COMMIT:=e185d7fd85499c8ce5ca2a54f5cf8fe7dbe3f8df
$(PKG)_MBEDTLS_HASH:=052dccf3a404dce25a467c6fe044b0c858d609ace8e883b59e9dfd479fdd4528
$(PKG)_MBEDTLS_SITE:=https://github.com/Mbed-TLS/mbedtls/archive

# mbedTLS 4.x is itself a git repository with a submodule (framework/, the
# Mbed-TLS/mbedtls-framework repository) and its CMakeLists.txt aborts with
# "not found (and does not appear to be a git checkout)" when
# framework/CMakeLists.txt is missing, so that tarball is fetched as well.
$(PKG)_MBEDTLS_FW_COMMIT:=457996474728cb8e968ed21953b72f74d2f536b2
$(PKG)_MBEDTLS_FW_HASH:=c15bcc24fc43bdf325b0e04fa63270daf6e9488167b94b46547d8134efa9c906
$(PKG)_MBEDTLS_FW_SITE:=https://github.com/Mbed-TLS/mbedtls-framework/archive

$(PKG)_BUILD_DIR:=$($(PKG)_DIR)/freetz-build
$(PKG)_BINARIES:=ot-daemon ot-ctl
$(PKG)_BINARIES_BUILD_DIR:=$(addprefix $($(PKG)_BUILD_DIR)/src/posix/,$($(PKG)_BINARIES))
$(PKG)_BINARIES_TARGET_DIR:=$($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/bin/%)

$(PKG)_DEPENDS_ON += $(if $(FREETZ_TARGET_UCLIBC_HAS_multiple_libs),libpthread libutil librt)

# --------------------------------------------------------------------------
# Configure
# --------------------------------------------------------------------------
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.10
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_PROCESSOR=$(FREETZ_TARGET_ARCH)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY

# POSIX platform (Linux). Upstream offers the applications as an either/or
# selection: OT_APP_DAEMON builds ot-daemon + ot-ctl, OT_APP_CLI would build a
# standalone ot-cli instead. The daemon is selected because ot-ctl offers the
# same command set while the Thread stack keeps running in the background.
$(PKG)_CONFIGURE_OPTIONS += -DOT_PLATFORM=posix
$(PKG)_CONFIGURE_OPTIONS += -DOT_BUILD_EXECUTABLES=ON
$(PKG)_CONFIGURE_OPTIONS += -DOT_APP_DAEMON=ON
$(PKG)_CONFIGURE_OPTIONS += -DOT_APP_CLI=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOT_DAEMON=ON
$(PKG)_CONFIGURE_OPTIONS += -DOT_FTD=ON
$(PKG)_CONFIGURE_OPTIONS += -DOT_MTD=ON
$(PKG)_CONFIGURE_OPTIONS += -DOT_RCP=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOT_LINKER_MAP=OFF
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TESTING=OFF

# 32-bit targets: 64-bit atomics are resolved through libatomic (see the same
# workaround in ffmpeg/cmus/openssl).
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_EXE_LINKER_FLAGS="-latomic"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# --------------------------------------------------------------------------
# mbedTLS submodule
# --------------------------------------------------------------------------
$(DL_DIR)/openthread-mbedtls-$(OPENTHREAD_MBEDTLS_COMMIT).tar.gz: | $(DL_DIR)
	$(DL_TOOL) -o openthread-mbedtls-$(OPENTHREAD_MBEDTLS_COMMIT).tar.gz $(DL_DIR) \
		$(OPENTHREAD_MBEDTLS_COMMIT).tar.gz $(OPENTHREAD_MBEDTLS_SITE) $(OPENTHREAD_MBEDTLS_HASH)

$(DL_DIR)/openthread-mbedtls-framework-$(OPENTHREAD_MBEDTLS_FW_COMMIT).tar.gz: | $(DL_DIR)
	$(DL_TOOL) -o openthread-mbedtls-framework-$(OPENTHREAD_MBEDTLS_FW_COMMIT).tar.gz $(DL_DIR) \
		$(OPENTHREAD_MBEDTLS_FW_COMMIT).tar.gz $(OPENTHREAD_MBEDTLS_FW_SITE) $(OPENTHREAD_MBEDTLS_FW_HASH)

$(OPENTHREAD_DIR)/.mbedtls-unpacked: $(DL_DIR)/openthread-mbedtls-$(OPENTHREAD_MBEDTLS_COMMIT).tar.gz $(DL_DIR)/openthread-mbedtls-framework-$(OPENTHREAD_MBEDTLS_FW_COMMIT).tar.gz $(OPENTHREAD_DIR)/.unpacked
	$(RM) -r $(OPENTHREAD_DIR)/third_party/mbedtls/repo
	mkdir -p $(OPENTHREAD_DIR)/third_party/mbedtls/repo
	$(call UNPACK_TARBALL,$(DL_DIR)/openthread-mbedtls-$(OPENTHREAD_MBEDTLS_COMMIT).tar.gz,$(OPENTHREAD_DIR)/third_party/mbedtls/repo,1)
	mkdir -p $(OPENTHREAD_DIR)/third_party/mbedtls/repo/framework
	$(call UNPACK_TARBALL,$(DL_DIR)/openthread-mbedtls-framework-$(OPENTHREAD_MBEDTLS_FW_COMMIT).tar.gz,$(OPENTHREAD_DIR)/third_party/mbedtls/repo/framework,1)
	@touch $@

# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.build-prereq-checked $($(PKG)_DIR)/.unpacked $($(PKG)_DIR)/.mbedtls-unpacked $(OPENTHREAD_MAKE_DIR)/$(pkg).mk
	@$(call _ECHO,configuring)
	$(RM) -r $(OPENTHREAD_BUILD_DIR)
	mkdir -p $(OPENTHREAD_BUILD_DIR)
	cd $(OPENTHREAD_BUILD_DIR); \
		$(MAKE_ENV) $(TARGET_CONFIGURE_ENV) \
		$(CMAKE) .. \
		$(OPENTHREAD_CONFIGURE_OPTIONS)
	@touch $@

$($(PKG)_BUILD_DIR)/.built: $($(PKG)_DIR)/.configured
	@$(call _ECHO,building)
	$(SUBMAKE) -C $(OPENTHREAD_BUILD_DIR)
	@touch $@

$($(PKG)_DIR)/.install-dirs:
	mkdir -p $(OPENTHREAD_DEST_DIR)/usr/bin
	@touch $@

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_BUILD_DIR)/.built $($(PKG)_DIR)/.install-dirs ;

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/bin)))

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	$(RM) -r $(OPENTHREAD_BUILD_DIR) $(OPENTHREAD_DIR)/.configured $(OPENTHREAD_DIR)/.mbedtls-unpacked $(OPENTHREAD_DIR)/.install-dirs

$(pkg)-uninstall:
	$(RM) $(OPENTHREAD_BINARIES_TARGET_DIR)

$(PKG_FINISH)
