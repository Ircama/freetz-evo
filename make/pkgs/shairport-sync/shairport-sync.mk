$(call PKG_INIT_BIN, 5.0.4)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b89d4af74cffadd83d1be6eaf4e967180aa5a6aed32f561c937ae1d787909c25
$(PKG)_SITE:=https://github.com/mikebrady/shairport-sync/archive/refs/tags
### WEBSITE:=https://github.com/mikebrady/shairport-sync
### CHANGES:=https://github.com/mikebrady/shairport-sync/releases
### CVSREPO:=https://github.com/mikebrady/shairport-sync

$(PKG)_CATEGORY:=Audio

$(PKG)_BINARY:=$($(PKG)_DIR)/shairport-sync
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/shairport-sync
$(PKG)_TARGET_SANITIZED_MARKER:=$($(PKG)_DEST_DIR)/.sanitized

$(PKG)_STATUS_CACHE_SOURCE:=$(MAKE_DIR)/pkgs/$(pkg)/files/shairport-sync-status-cache.c
$(PKG)_STATUS_CACHE_BINARY:=$($(PKG)_DIR)/shairport-sync-status-cache
$(PKG)_STATUS_CACHE_TARGET:=$($(PKG)_DEST_DIR)/usr/bin/shairport-sync-status-cache

$(PKG)_DEPENDS_ON += alsa-lib libconfig libdaemon popt openssl

$(PKG)_PATCH_POST_CMDS += $(RM) compile config.guess config.sub depcomp install-sh ltmain.sh missing;
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --with-alsa
$(PKG)_CONFIGURE_OPTIONS += --with-tinysvcmdns
$(PKG)_CONFIGURE_OPTIONS += --with-libdaemon
$(PKG)_CONFIGURE_OPTIONS += --with-metadata
$(PKG)_CONFIGURE_OPTIONS += --with-ssl=openssl
$(PKG)_CONFIGURE_OPTIONS += --without-soxr
$(PKG)_CONFIGURE_OPTIONS += --without-avahi
$(PKG)_CONFIGURE_OPTIONS += --without-pulseaudio
$(PKG)_CONFIGURE_OPTIONS += --without-pipewire
$(PKG)_CONFIGURE_OPTIONS += --without-jack
$(PKG)_CONFIGURE_OPTIONS += --without-ao
$(PKG)_CONFIGURE_OPTIONS += --without-sndio
$(PKG)_CONFIGURE_OPTIONS += --without-soundio
$(PKG)_CONFIGURE_OPTIONS += --without-stdout
$(PKG)_CONFIGURE_OPTIONS += --without-pipe
$(PKG)_CONFIGURE_OPTIONS += --without-dummy
$(PKG)_CONFIGURE_OPTIONS += --without-dbus-interface
$(PKG)_CONFIGURE_OPTIONS += --without-mpris-interface
$(PKG)_CONFIGURE_OPTIONS += --without-mqtt-client
$(PKG)_CONFIGURE_OPTIONS += --without-convolution
$(PKG)_CONFIGURE_OPTIONS += --without-airplay-2
$(PKG)_CONFIGURE_OPTIONS += --without-ffmpeg
$(PKG)_CONFIGURE_OPTIONS += --without-apple-alac
$(PKG)_CONFIGURE_OPTIONS += --without-systemv-startup
$(PKG)_CONFIGURE_OPTIONS += --without-systemd-startup
$(PKG)_CONFIGURE_OPTIONS += --without-freebsd-startup
$(PKG)_CONFIGURE_OPTIONS += --without-cygwin-startup
$(PKG)_CONFIGURE_OPTIONS += --without-configfiles
$(PKG)_CONFIGURE_OPTIONS += --without-create-user-group
$(PKG)_CONFIGURE_OPTIONS += --with-piddir=/var/run

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_TARGET_SANITIZED_MARKER): $($(PKG)_DIR)/.configured
	$(RM) -r \
		$(SHAIRPORT_SYNC_DEST_DIR)/etc/default.shairport-sync \
		$(SHAIRPORT_SYNC_DEST_DIR)/etc/init.d/rc.shairport-sync \
		$(SHAIRPORT_SYNC_DEST_DIR)/usr/lib/cgi-bin/shairport-sync \
		$(SHAIRPORT_SYNC_DEST_DIR)/usr/lib/cgi-bin/shairport-sync.cgi
	mkdir -p $(SHAIRPORT_SYNC_DEST_DIR)
	touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(SHAIRPORT_SYNC_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY) $($(PKG)_TARGET_SANITIZED_MARKER)
	$(INSTALL_BINARY_STRIP)

$($(PKG)_STATUS_CACHE_BINARY): $($(PKG)_STATUS_CACHE_SOURCE) $($(PKG)_DIR)/.configured
	$(MAKE_ENV) \
		$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -Wall -Wextra -Os -std=c99 -o $@ $<

$($(PKG)_STATUS_CACHE_TARGET): $($(PKG)_STATUS_CACHE_BINARY) $($(PKG)_TARGET_SANITIZED_MARKER)
	mkdir -p $(dir $@)
	cp $< $@
	$(TARGET_STRIP) $@ 2>/dev/null || true

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_SANITIZED_MARKER) $($(PKG)_TARGET_BINARY) $($(PKG)_STATUS_CACHE_TARGET)

$(pkg)-clean:
	-$(SUBMAKE) -C $(SHAIRPORT_SYNC_DIR) clean
	$(RM) $($(PKG)_STATUS_CACHE_BINARY) $($(PKG)_TARGET_SANITIZED_MARKER)

$(pkg)-uninstall:
	$(RM) \
		$(SHAIRPORT_SYNC_TARGET_BINARY) \
		$(SHAIRPORT_SYNC_STATUS_CACHE_TARGET) \
		$(SHAIRPORT_SYNC_TARGET_SANITIZED_MARKER)

$(PKG_FINISH)