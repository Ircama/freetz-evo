$(call PKG_INIT_BIN, 5.15.23)
$(PKG)_CATEGORY:=Disk Clone
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=clonezilla-v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=b04e4b3c21113b5307935955bb717bab6e5ef87941910c218f37a286a52915f4
$(PKG)_SITE:=https://github.com/stevenshiau/clonezilla/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/clonezilla-$($(PKG)_VERSION)
### WEBSITE:=https://clonezilla.org/
### MANPAGE:=https://clonezilla.org/clonezilla-live.php
### CHANGES:=https://github.com/stevenshiau/clonezilla/tags
### CVSREPO:=https://github.com/stevenshiau/clonezilla

$(PKG)_TARGET_SUPPORT_STAMP:=$($(PKG)_DIR)/.compiled
$(PKG)_TARGET_DRBL_DIR:=$($(PKG)_DEST_DIR)/usr/share/drbl
$(PKG)_TARGET_BINARIES:=$($(PKG)_DEST_DIR)/usr/sbin/clonezilla $($(PKG)_DEST_DIR)/usr/sbin/ocs-sr $($(PKG)_DEST_DIR)/usr/sbin/ocs-onthefly

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
