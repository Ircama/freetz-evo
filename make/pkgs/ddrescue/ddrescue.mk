$(call PKG_INIT_BIN, 1.30)
$(PKG)_CATEGORY_PKGS:=Data Migration and Disaster Recovery
$(PKG)_SOURCE:=gddrescue_$($(PKG)_VERSION).orig.tar.gz
$(PKG)_HASH:=d01c9ff0599a13d10261c9b435333cc4aaff016be226788cfe515329c221789a
$(PKG)_SITE:=https://deb.debian.org/debian/pool/main/g/gddrescue
$(PKG)_DIR:=$(SOURCE_DIR)/gddrescue-$($(PKG)_VERSION)
### WEBSITE:=https://www.gnu.org/software/ddrescue/
### MANPAGE:=https://www.gnu.org/software/ddrescue/manual/ddrescue_manual.html
### CHANGES:=https://ftp.gnu.org/gnu/ddrescue/
### STEWARD:=Ircama

$(PKG)_BINARIES:=ddrescue ddrescuelog
$(PKG)_BINARIES_BUILD_DIR:=$(addprefix $($(PKG)_DIR)/,$($(PKG)_BINARIES))
$(PKG)_BINARIES_TARGET_DIR:=$(addprefix $($(PKG)_DEST_DIR)/usr/bin/,$($(PKG)_BINARIES))

DDRESCUE_CPPFLAGS:=

ifeq ($(strip $(FREETZ_TARGET_UCLIBC_0_9_32)),y)
DDRESCUE_CPPFLAGS += -DDDRESCUE_MISSING_POSIX_FALLOCATE=1
endif

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARIES_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(DDRESCUE_DIR) V=1 all \
		CXX="$(TARGET_CXX)" \
		CPPFLAGS="$(TARGET_CFLAGS) $(DDRESCUE_CPPFLAGS)" \
		CXXFLAGS="$(TARGET_CFLAGS)" \
		LDFLAGS="$(TARGET_LDFLAGS)"

$(foreach binary,$($(PKG)_BINARIES_BUILD_DIR),$(eval $(call INSTALL_BINARY_STRIP_RULE,$(binary),/usr/bin)))

$(pkg):

$(pkg)-precompiled: $($(PKG)_BINARIES_TARGET_DIR)

$(pkg)-clean:
	@if [ -f "$(DDRESCUE_DIR)/Makefile" ]; then \
		$(SUBMAKE) -C $(DDRESCUE_DIR) clean; \
	fi

$(pkg)-uninstall:
	$(RM) $(DDRESCUE_BINARIES:%=$(DDRESCUE_DEST_DIR)/usr/bin/%)

$(PKG_FINISH)
