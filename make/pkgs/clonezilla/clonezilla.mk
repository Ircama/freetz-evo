$(call PKG_INIT_BIN, 5.15.23)
$(PKG)_CATEGORY_PKGS:=Data Migration and Disaster Recovery

# clonezilla requires uClibc 1.0.58 or newer: it depends on fsarchiver and
# partclone, which need libblkid from util-linux 2.41. The option is gated
# by "depends on FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in.

$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=clonezilla-v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b04e4b3c21113b5307935955bb717bab6e5ef87941910c218f37a286a52915f4
$(PKG)_SITE:=https://github.com/stevenshiau/clonezilla/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/clonezilla-$($(PKG)_VERSION)
### WEBSITE:=https://clonezilla.org/
### MANPAGE:=https://clonezilla.org/clonezilla-live.php
### CHANGES:=https://github.com/stevenshiau/clonezilla/tags
### CVSREPO:=https://github.com/stevenshiau/clonezilla
### STEWARD:=Ircama

$(PKG)_TARGET_SUPPORT_STAMP:=$($(PKG)_DIR)/.compiled
$(PKG)_TARGET_DRBL_DIR:=$($(PKG)_DEST_DIR)/usr/share/drbl
$(PKG)_TARGET_BINARIES:=$($(PKG)_DEST_DIR)/usr/sbin/clonezilla $($(PKG)_DEST_DIR)/usr/sbin/ocs-sr $($(PKG)_DEST_DIR)/usr/sbin/ocs-onthefly
$(PKG)_FILES_DIR:=$($(PKG)_MAKE_DIR)/files/root
$(PKG)_BASH3_FIXER:=$($(PKG)_MAKE_DIR)/files/patch-ocs-functions-for-bash3.sh
$(PKG)_TEE_FIXER:=$($(PKG)_MAKE_DIR)/files/patch-scripts-for-bb-tee.sh
$(PKG)_OCS_ONTHEFLY_FIXER:=$($(PKG)_MAKE_DIR)/files/patch-ocs-onthefly-src-pt-info.sh

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_SUPPORT_STAMP): $($(PKG)_DIR)/.configured
	mkdir -p $(CLONEZILLA_TARGET_DRBL_DIR)
	mkdir -p $(CLONEZILLA_DEST_DIR)/etc/drbl
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/bin
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/sbin
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/conf
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/scripts
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/setup
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/toolbox
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/themes
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/prerun
	rm -rf $(CLONEZILLA_TARGET_DRBL_DIR)/postrun
	$(call COPY_USING_TAR,$(CLONEZILLA_DIR),$(CLONEZILLA_TARGET_DRBL_DIR),--exclude=LICENSE --exclude=Makefile --exclude=README --exclude=clonezilla.spec --exclude=debian --exclude=dev.branch --exclude=doc --exclude=samples .)
	$(SHELL) $(CLONEZILLA_BASH3_FIXER) $(CLONEZILLA_TARGET_DRBL_DIR)/scripts/sbin/ocs-functions
	$(SHELL) $(CLONEZILLA_TEE_FIXER) $(CLONEZILLA_TARGET_DRBL_DIR)
	$(SHELL) $(CLONEZILLA_OCS_ONTHEFLY_FIXER) $(CLONEZILLA_TARGET_DRBL_DIR)/sbin/ocs-onthefly
	install -D -m 755 $(CLONEZILLA_FILES_DIR)/usr/share/drbl/sbin/drbl-functions $(CLONEZILLA_TARGET_DRBL_DIR)/sbin/drbl-functions
	install -D -m 755 $(CLONEZILLA_FILES_DIR)/usr/share/drbl/sbin/drbl-conf-functions $(CLONEZILLA_TARGET_DRBL_DIR)/sbin/drbl-conf-functions
	install -D -m 755 $(CLONEZILLA_FILES_DIR)/usr/share/drbl/sbin/tee $(CLONEZILLA_TARGET_DRBL_DIR)/sbin/tee
	install -D -m 755 $(CLONEZILLA_FILES_DIR)/usr/share/drbl/sbin/mountpoint $(CLONEZILLA_TARGET_DRBL_DIR)/sbin/mountpoint
	install -D -m 644 $(CLONEZILLA_FILES_DIR)/usr/share/drbl/lang/bash/en_US $(CLONEZILLA_TARGET_DRBL_DIR)/lang/bash/en_US
	ln -sf en_US $(CLONEZILLA_TARGET_DRBL_DIR)/lang/bash/en_US.UTF-8
	cp -f $(CLONEZILLA_DIR)/conf/drbl-ocs.conf $(CLONEZILLA_DEST_DIR)/etc/drbl/drbl-ocs.conf
	ln -sf ../scripts/sbin/ocs-functions $(CLONEZILLA_TARGET_DRBL_DIR)/sbin/ocs-functions
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_SUPPORT_STAMP) $($(PKG)_TARGET_BINARIES)

$(pkg)-clean:
	$(RM) $(CLONEZILLA_DIR)/.compiled

$(pkg)-uninstall:
	$(RM) $(CLONEZILLA_TARGET_BINARIES)
	$(RM) -r $(CLONEZILLA_DEST_DIR)/usr/share/drbl

$(PKG_FINISH)
