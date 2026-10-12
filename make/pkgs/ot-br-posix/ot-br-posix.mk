# ot-br-posix v2026.10.0 -- OpenThread Border Router (POSIX/Linux agent).
#
# otbr-agent is the Thread Border Router: it owns the Radio Co-Processor (RCP)
# over spinel, creates and routes the Thread network, and publishes the border
# router services with OpenThread's own mDNS/DNS-SD stack (OTBR_MDNS=openthread),
# so no mDNSResponder/Bonjour or Avahi port is needed.
#
# Feature selection (all optional components are switched off, which removes the
# protobuf, dbus, jsoncpp and libsystemd dependencies):
#   OTBR_MDNS=openthread   use the OpenThread core mDNS/DNS-SD implementation
#   OTBR_DBUS=OFF          no D-Bus API (would need protobuf)
#   OTBR_WEB=OFF           no web GUI (would need protobuf + jsoncpp)
#   OTBR_REST=OFF          no REST server (would need cJSON + cpp-httplib)
#   OTBR_NAT64=OFF         no NAT64 (no libnetfilter_queue/ipset setup)
#   OTBR_DHCP6_PD=OFF      no DHCPv6-PD
#   OTBR_BACKBONE_ROUTER=OFF
#   OTBR_NFTABLES=OFF      ingress firewall producer stays the OT posix one
#
# The OpenThread sources are not vendored in this repository but taken from the
# openthread package (same version, matching Thread feature set): a symlink from
# third_party/openthread/repo to the openthread source directory is created
# before configure runs, because upstream hardcodes the path with a plain
# "set(OPENTHREAD_PROJECT_DIRECTORY ...)" that cannot be overridden on the
# command line. The other submodules of this repository (third_party/cJSON and
# third_party/cpp-httplib) belong to the REST component and are not needed.
$(call PKG_INIT_BIN, 2026.10.0)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Home Automation

$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=38bfb768e3732adfb032c315048b7f3639427547151fe1df6fbbbc28127154e8
$(PKG)_SITE:=https://github.com/openthread/ot-br-posix/archive/refs/tags
### WEBSITE:=https://github.com/openthread/ot-br-posix
### CHANGES:=https://github.com/openthread/ot-br-posix/releases
### CVSREPO:=https://github.com/openthread/ot-br-posix

$(PKG)_BUILD_DIR:=$($(PKG)_DIR)/freetz-build
$(PKG)_BINARIES:=otbr-agent ot-ctl
$(PKG)_BINARIES_BUILD_DIR:=$($(PKG)_BUILD_DIR)/src/agent/otbr-agent \
	$($(PKG)_BUILD_DIR)/third_party/openthread/repo/src/posix/ot-ctl
$(PKG)_BINARIES_TARGET_DIR:=$($(PKG)_BINARIES:%=$($(PKG)_DEST_DIR)/usr/sbin/%)

$(PKG)_DEPENDS_ON += openthread
$(PKG)_DEPENDS_ON += $(if $(FREETZ_TARGET_UCLIBC_HAS_multiple_libs),libpthread libutil librt)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_OPENTHREAD

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
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TESTING=OFF

$(PKG)_CONFIGURE_OPTIONS += -DOTBR_MDNS=openthread
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_DBUS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_WEB=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_REST=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_NAT64=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_DHCP6_PD=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_BACKBONE_ROUTER=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_NFTABLES=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_PF=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_FEATURE_FLAGS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_TELEMETRY_DATA_API=OFF
$(PKG)_CONFIGURE_OPTIONS += -DOTBR_INFRA_IF_NAME=br0

# 32-bit targets: 64-bit atomics are resolved through libatomic.
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_EXE_LINKER_FLAGS="-latomic"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# --------------------------------------------------------------------------
# OpenThread sources (symlinked from the openthread package)
# --------------------------------------------------------------------------
$($(PKG)_DIR)/.openthread-src: $($(PKG)_DIR)/.unpacked $(OPENTHREAD_DIR)/.unpacked $(OPENTHREAD_DIR)/.mbedtls-unpacked
	$(RM) -r $(OT_BR_POSIX_DIR)/third_party/openthread/repo
	ln -sfn $(abspath $(OPENTHREAD_DIR)) $(OT_BR_POSIX_DIR)/third_party/openthread/repo
	@touch $@

# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.build-prereq-checked $($(PKG)_DIR)/.unpacked $($(PKG)_DIR)/.openthread-src $(OT_BR_POSIX_MAKE_DIR)/$(pkg).mk
	@$(call _ECHO,configuring)
	$(RM) -r $(OT_BR_POSIX_BUILD_DIR)
	mkdir -p $(OT_BR_POSIX_BUILD_DIR)
	cd $(OT_BR_POSIX_BUILD_DIR); \
		$(MAKE_ENV) $(TARGET_CONFIGURE_ENV) \
		$(CMAKE) .. \
		$(OT_BR_POSIX_CONFIGURE_OPTIONS)
	@touch $@

$($(PKG)_BUILD_DIR)/.built: $($(PKG)_DIR)/.configured
	@$(call _ECHO,building)
	$(SUBMAKE) -C $(OT_BR_POSIX_BUILD_DIR)
	@touch $@

$($(PKG)_DIR)/.install-dirs:
	mkdir -p $(OT_BR_POSIX_DEST_DIR)/usr/sbin
	@touch $@

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_BUILD_DIR)/.built $($(PKG)_DIR)/.install-dirs ;

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/sbin)))

# Runtime integration: init script and the configuration used by the freetz
# configuration framework (/etc/default.otbr/otbr.cfg is linked into
# /mod/etc/default.otbr by the mod package, saved values go to
# /mod/etc/conf/otbr.cfg).
$(PKG)_STAGING_SOURCES := \
	$(OT_BR_POSIX_MAKE_DIR)/files/root/etc/default.otbr/otbr.cfg \
	$(OT_BR_POSIX_MAKE_DIR)/files/root/etc/default.otbr/otbr.save \
	$(OT_BR_POSIX_MAKE_DIR)/files/root/etc/init.d/rc.otbr
$(PKG)_STAGING_TARGET := $($(PKG)_DEST_DIR)/etc/init.d/rc.otbr

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(OT_BR_POSIX_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(OT_BR_POSIX_MAKE_DIR)/files,$(OT_BR_POSIX_TARGET_DIR))
	chmod 755 \
		$(OT_BR_POSIX_DEST_DIR)/etc/init.d/rc.otbr \
		$(OT_BR_POSIX_DEST_DIR)/etc/default.otbr/otbr.save

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR) $($(PKG)_STAGING_TARGET)

$(pkg)-clean:
	$(RM) -r $(OT_BR_POSIX_BUILD_DIR) $(OT_BR_POSIX_DIR)/.configured $(OT_BR_POSIX_DIR)/.openthread-src $(OT_BR_POSIX_DIR)/.install-dirs

$(pkg)-uninstall:
	$(RM) $(OT_BR_POSIX_BINARIES_TARGET_DIR)

$(PKG_FINISH)
