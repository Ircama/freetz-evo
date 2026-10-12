# freetz-matter -- expose the FRITZ!Box as a Matter device (rs-matter).
#
# The Rust sources of this package live in its src/ directory in the repository
# and are copied into the package source directory under source/ before the
# build, because freetz removes $(PKG)_DIR while preparing a package (setting
# $(PKG)_DIR to the repository directory would delete the package itself).
# Same pattern as the matter-bridge and ariang packages.
#
# Unlike the other Rust packages in this tree there is no upstream tarball: the
# only download is the `rs-matter` git checkout that cargo fetches itself at
# build time, pinned to the revision verified here (see Cargo.toml).
$(call PKG_INIT_BIN, 0.1)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Home Automation

# rs-matter revision this application is written and verified against; keep it
# in sync with the `rev` in the package Cargo.toml.
FREETZ_MATTER_RS_MATTER_REV:=7d5684f495fe5bca03d993647543508ab7587f10

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
$(eval $(call RUST_DEPENDS_VARS))

FREETZ_MATTER_CARGO_HOME:=$(abspath $($(PKG)_DIR)/.cargo)

$(PKG)_BINARY:=$($(PKG)_DIR)/target/$($(PKG)_RUST_TARGET_DIR)/release/freetz-matter
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/freetz-matter

# `amixer` (alsa-utils) is the actuator behind the Smart Speaker endpoint: the
# OnOff and LevelControl clusters map to mute/unmute and to the PCM volume.
$(PKG)_DEPENDS_ON += alsa-utils
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ALSA_UTILS

# This package has no tarball to download: the sources are copied from the
# package directory into the (freetz owned) source directory.
$($(PKG)_DIR)/.unpacked: $(FREETZ_MATTER_MAKE_DIR)/Cargo.toml \
		$(FREETZ_MATTER_MAKE_DIR)/src/main.rs \
		$(FREETZ_MATTER_MAKE_DIR)/src/boxdata.rs | $(SOURCE_DIR)
	@$(call _ECHO,preparing)
	mkdir -p $(FREETZ_MATTER_DIR)/src
	cp $(FREETZ_MATTER_MAKE_DIR)/src/*.rs $(FREETZ_MATTER_DIR)/src/
	cp $(FREETZ_MATTER_MAKE_DIR)/Cargo.toml $(FREETZ_MATTER_DIR)/
	@touch $@

$(PKG_CONFIGURED_NOP)

# rs-matter's IDL codegen produces ~30 MB of Rust (see Cargo.toml), so the build
# is deliberately serialized: one cargo job and one rustc thread keep the peak
# memory within reach of a small build host (a single rustc job peaks at ~5.6 GB
# RSS for this crate).
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@$(call _ECHO,building)
	cd $(FREETZ_MATTER_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(FREETZ_MATTER_DIR))"; \
	export CARGO_HOME="$(FREETZ_MATTER_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-Zthreads=1"]\n' \
		"$(FREETZ_MATTER_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	export CARGO_BUILD_JOBS=1; \
	cargo +nightly fetch --target "$(FREETZ_MATTER_RUST_TARGET_DIR)"; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT,1.1.5) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.3) \
	cargo +nightly build --release $(FREETZ_MATTER_CARGO_BUILD_STD_FLAGS) \
		--target "$(FREETZ_MATTER_RUST_TARGET_ARG)"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg): $($(PKG)_BINARY)

# Web interface page (Freetz menu entry "freetz-matter (Matter device)")
$($(PKG)_DEST_DIR)/usr/lib/cgi-bin/freetz-matter.cgi: $(FREETZ_MATTER_MAKE_DIR)/files/root/usr/lib/cgi-bin/freetz-matter.cgi
	mkdir -p $(dir $@)
	cp $< $@
	chmod 755 $@

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_DEST_DIR)/usr/lib/cgi-bin/freetz-matter.cgi

$(pkg)-clean:
	$(RM) -r $(FREETZ_MATTER_DIR)/target

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
