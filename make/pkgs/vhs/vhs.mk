$(call PKG_INIT_BIN, 0.11.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=c08b8502989fe7e9626c02938f3fc512c2a4ba21f839f455d20d7eb1da7bc39f
$(PKG)_SITE:=https://github.com/charmbracelet/vhs/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/vhs-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/charmbracelet/vhs
### MANPAGE:=https://github.com/charmbracelet/vhs#readme
### CHANGES:=https://github.com/charmbracelet/vhs/releases
### CVSREPO:=https://github.com/charmbracelet/vhs
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/vhs
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/vhs

$(PKG)_GO_VERSION := 1.25.10

$(PKG)_DEPENDS_ON += go-host
$(PKG)_DEPENDS_ON += ffmpeg ttyd

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_FFMPEG_ffmpeg
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_FFMPEG_DECODER_png
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_FFMPEG_DEMUXER_image2
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_FFMPEG_PROTOCOL_file
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_TTYD

$(PKG)_GO_OS := linux
$(PKG)_GO_ARCH := $(if $(FREETZ_TARGET_ARCH_MIPS),mips,$(if $(FREETZ_TARGET_ARCH_ARM),arm,$(if $(FREETZ_TARGET_ARCH_X86),386,$(if $(FREETZ_TARGET_ARCH_AARCH64),arm64,unknown))))
$(PKG)_GO_MIPS := $(if $(FREETZ_TARGET_ARCH_MIPS),softfloat,)
$(PKG)_GO_ARM := $(if $(FREETZ_TARGET_ARCH_ARM),$(if $(FREETZ_TARGET_ARCH_ARM_NEON),7,6),)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@echo "Building vhs with Go $(VHS_GO_VERSION)..."
	cd $(VHS_DIR); \
	export PATH=$(TOOLS_DIR)/go-host/bin:$$PATH; \
	GOOS=$(VHS_GO_OS) \
	GOARCH=$(VHS_GO_ARCH) \
	$(if $(VHS_GO_MIPS),GOMIPS=$(VHS_GO_MIPS),) \
	$(if $(VHS_GO_ARM),GOARM=$(VHS_GO_ARM),) \
	CGO_ENABLED=0 \
	go build \
		-v \
		-buildvcs=false \
		-trimpath \
		-ldflags="-s -w" \
		-o vhs \
		.

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(VHS_DIR) clean
	$(RM) $(VHS_BINARY) $(VHS_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(VHS_TARGET_BINARY)

$(PKG_FINISH)