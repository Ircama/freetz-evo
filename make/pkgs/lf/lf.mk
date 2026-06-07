$(call PKG_INIT_BIN, 41)
$(PKG)_SOURCE_DOWNLOAD_NAME:=r$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=55c556d53b5541d5f8691f1309a0166a7a0d8e06cb051c3030c2cd7d8abc6789
$(PKG)_SITE:=https://github.com/gokcehan/lf/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/lf-r$($(PKG)_VERSION)
### WEBSITE:=https://github.com/gokcehan/lf
### MANPAGE:=https://github.com/gokcehan/lf/blob/master/doc.md
### CHANGES:=https://github.com/gokcehan/lf/releases
### CVSREPO:=https://github.com/gokcehan/lf
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/lf
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/lf

$(PKG)_GO_VERSION := 1.25.10

$(PKG)_DEPENDS_ON += go-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64

$(PKG)_GO_OS := linux
$(PKG)_GO_ARCH := $(FREETZ_TARGET_GO_ARCH)
$(PKG)_GO_MIPS := $(FREETZ_TARGET_GO_MIPS)
$(PKG)_GO_ARM := $(FREETZ_TARGET_GO_ARM)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@echo "Building lf with Go $(LF_GO_VERSION)..."
	cd $(LF_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(LF_GO_OS) \
	GOARCH=$(LF_GO_ARCH) \
	$(if $(LF_GO_MIPS),GOMIPS=$(LF_GO_MIPS),) \
	$(if $(LF_GO_ARM),GOARM=$(LF_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w -X main.gVersion=r$(LF_VERSION)" \
		-o lf \
		.

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	mkdir -p $(dir $@)
	cp $< $@
	chmod 755 $@
	$(TARGET_STRIP) $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $($(PKG)_DIR) clean
	$(RM) $($(PKG)_BINARY) $($(PKG)_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)