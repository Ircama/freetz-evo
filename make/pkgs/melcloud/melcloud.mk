$(call PKG_INIT_BIN, 1.0)
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += curl

$(PKG)_STAGING_SOURCES := \
	$(MELCLOUD_MAKE_DIR)/files/.language \
	$(MELCLOUD_MAKE_DIR)/files/src/melcloud_cli.c \
	$(MELCLOUD_MAKE_DIR)/files/root/etc/default.melcloud/melcloud.cfg \
	$(MELCLOUD_MAKE_DIR)/files/root/etc/default.melcloud/melcloud.save \
	$(MELCLOUD_MAKE_DIR)/files/root/etc/init.d/rc.melcloud \
	$(MELCLOUD_MAKE_DIR)/files/root/usr/lib/cgi-bin/melcloud.cgi \
	$(MELCLOUD_MAKE_DIR)/files/root/usr/mww/melcloud/index.html

$(PKG)_TARGET_BINARY := $($(PKG)_DEST_DIR)/usr/bin/melcloud-cli
$(PKG)_STAGING_TARGET := $(MELCLOUD_DEST_DIR)/usr/lib/cgi-bin/melcloud.cgi

$($(PKG)_TARGET_BINARY): $(MELCLOUD_MAKE_DIR)/files/src/melcloud_cli.c | $(PACKAGES_DIR)
	mkdir -p $(MELCLOUD_DEST_DIR)/usr/bin
	$(MAKE_ENV) $(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) $(TARGET_LDFLAGS) \
		-Wall -Wextra -Os \
		$(MELCLOUD_MAKE_DIR)/files/src/melcloud_cli.c \
		-o $(MELCLOUD_TARGET_BINARY) -lcurl
	chmod 755 $(MELCLOUD_TARGET_BINARY)

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(MELCLOUD_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(MELCLOUD_MAKE_DIR)/files,$(MELCLOUD_TARGET_DIR))
	chmod 755 \
		$(MELCLOUD_DEST_DIR)/etc/init.d/rc.melcloud \
		$(MELCLOUD_DEST_DIR)/usr/lib/cgi-bin/melcloud.cgi

$(PKG_UNPACKED)

$(pkg):

$(pkg)-precompiled:

$(pkg) $(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_STAGING_TARGET)

$(pkg)-clean:
	$(RM) $(MELCLOUD_TARGET_BINARY)

$(PKG_FINISH)
