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
FREETZ_MATTER_RS_MATTER_REV:=4d4fd3a2d821fb0105a340e244b10be44efd3646

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
$(eval $(call RUST_DEPENDS_VARS))

FREETZ_MATTER_CARGO_HOME:=$(abspath $($(PKG)_DIR)/.cargo)

# ---------------------------------------------------------------------------
# rs-matter and the ~60 crates it depends on are fetched by cargo, not by a
# tarball, so the download phase is the rule below: it fills a cache shared by
# both Matter packages (`build/cargo-matter-cache`) that lives outside
# $(PKG)_DIR, which freetz wipes when preparing the package. The cache is also
# where the uClibc patches are applied (the patch functions are idempotent, so
# the build finds them already patched); the build hard-links the cache into the
# package Cargo home and builds with `--offline`, which means a build never
# downloads anything. `make freetz-matter-download` (or `make sources`) runs the
# download explicitly; the build calls it as a prerequisite.
# ---------------------------------------------------------------------------
FREETZ_MATTER_CARGO_CACHE:=$(abspath $(TOPDIR)/$(BUILD_DIR))/cargo-matter-cache
FREETZ_MATTER_CARGO_DL_DIR:=$(FREETZ_MATTER_CARGO_CACHE)/$(pkg)
FREETZ_MATTER_CARGO_DL_STAMP:=$(FREETZ_MATTER_CARGO_CACHE)/$(pkg).fetched

$(PKG)_BINARY:=$($(PKG)_DIR)/target/$($(PKG)_RUST_TARGET_DIR)/release/freetz-matter
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/freetz-matter

# `amixer` (alsa-utils) is the actuator behind the Smart Speaker endpoint: the
# OnOff and LevelControl clusters map to mute/unmute and to the PCM volume.
$(PKG)_DEPENDS_ON += alsa-utils
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ALSA_UTILS

# This package has no tarball to download: the sources are copied from the
# package directory into the (freetz owned) source directory. Cargo.lock is
# copied as well and the build runs with `--locked`, so the dependency graph
# (and with it the crate versions the uClibc patches above expect) is the
# committed one and not whatever crates.io resolves at build time.
$($(PKG)_DIR)/.unpacked: $(FREETZ_MATTER_MAKE_DIR)/Cargo.toml \
		$(FREETZ_MATTER_MAKE_DIR)/Cargo.lock \
		$(FREETZ_MATTER_MAKE_DIR)/src/main.rs \
		$(FREETZ_MATTER_MAKE_DIR)/src/boxdata.rs \
		$(FREETZ_MATTER_MAKE_DIR)/src/mdns.rs | $(SOURCE_DIR)
	@$(call _ECHO,preparing)
	mkdir -p $(FREETZ_MATTER_DIR)/src
	cp $(FREETZ_MATTER_MAKE_DIR)/src/*.rs $(FREETZ_MATTER_DIR)/src/
	cp $(FREETZ_MATTER_MAKE_DIR)/Cargo.toml $(FREETZ_MATTER_MAKE_DIR)/Cargo.lock $(FREETZ_MATTER_DIR)/
	@touch $@

$(PKG_CONFIGURED_NOP)

# Download phase of a package without a tarball: fill the shared cache with the
# whole dependency graph (rs-matter is a git dependency pinned by the `rev` in
# Cargo.toml plus Cargo.lock) and apply the uClibc patches there, so the build
# only has to hard-link the result and can run `--offline`.
$(pkg)-download: $(FREETZ_MATTER_CARGO_DL_STAMP)

$(FREETZ_MATTER_CARGO_DL_STAMP): $(FREETZ_MATTER_MAKE_DIR)/Cargo.toml \
		$(FREETZ_MATTER_MAKE_DIR)/Cargo.lock \
		$(wildcard $(FREETZ_MATTER_MAKE_DIR)/src/*.rs)
	@$(call _ECHO,downloading)
	rm -rf $(FREETZ_MATTER_CARGO_DL_DIR)
	mkdir -p $(FREETZ_MATTER_CARGO_DL_DIR)/src
	cp $(FREETZ_MATTER_MAKE_DIR)/Cargo.toml $(FREETZ_MATTER_MAKE_DIR)/Cargo.lock $(FREETZ_MATTER_CARGO_DL_DIR)/
	cp $(FREETZ_MATTER_MAKE_DIR)/src/*.rs $(FREETZ_MATTER_CARGO_DL_DIR)/src/
	cd $(FREETZ_MATTER_CARGO_DL_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(FREETZ_MATTER_CARGO_CACHE)"; \
	export CARGO_HOME="$$HOME/.cargo"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo +nightly fetch --locked $(FREETZ_MATTER_CARGO_BUILD_STD_FLAGS) --target "$(FREETZ_MATTER_RUST_TARGET_DIR)" && \
	cargo +nightly fetch --locked && \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT,1.1.5) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.3) \
	true
	@touch $@

# rs-matter's IDL codegen produces ~30 MB of Rust (see Cargo.toml), so the build
# is deliberately serialized: one cargo job and one rustc thread, plus many
# codegen units in the release profile, keep the peak memory within reach of a
# small build host (with `codegen-units = 16` a single rustc job of rs-matter is
# OOM-killed at ~5.6 GB RSS here, `256` brings it down to a few hundred MB).
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured | $(FREETZ_MATTER_CARGO_DL_STAMP)
	@$(call _ECHO,building)
	cd $(FREETZ_MATTER_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(FREETZ_MATTER_DIR))"; \
	export CARGO_HOME="$(FREETZ_MATTER_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	$(call CARGO_LINK_DL_CACHE__INT,$(FREETZ_MATTER_CARGO_CACHE)/.cargo,$$CARGO_HOME) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-Zthreads=1"]\n' \
		"$(FREETZ_MATTER_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	export CARGO_BUILD_JOBS=1; \
	cargo +nightly fetch --locked --offline --target "$(FREETZ_MATTER_RUST_TARGET_DIR)"; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT,1.1.5) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.3) \
	cargo +nightly build --locked --offline --release $(FREETZ_MATTER_CARGO_BUILD_STD_FLAGS) \
		--target "$(FREETZ_MATTER_RUST_TARGET_ARG)"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg): $($(PKG)_BINARY)

# Static files (config defaults, save hook, init script, web page) are staged
# through an explicit target: the generic $($(PKG)_TARGET_DIR)/root rule has only
# an order-only prerequisite, so an existing staging directory is never
# refreshed and later rebuilds would keep stale copies of files/root.
$(PKG)_STAGING_SOURCES := \
	$(FREETZ_MATTER_MAKE_DIR)/files/.language \
	$(FREETZ_MATTER_MAKE_DIR)/files/root/etc/default.freetz-matter/freetz-matter.cfg \
	$(FREETZ_MATTER_MAKE_DIR)/files/root/etc/default.freetz-matter/freetz-matter.save \
	$(FREETZ_MATTER_MAKE_DIR)/files/root/etc/init.d/rc.freetz-matter \
	$(FREETZ_MATTER_MAKE_DIR)/files/root/usr/lib/cgi-bin/freetz-matter.cgi
$(PKG)_STAGING_TARGET := $($(PKG)_DEST_DIR)/etc/init.d/rc.freetz-matter

$($(PKG)_STAGING_TARGET): $($(PKG)_STAGING_SOURCES) | $(PACKAGES_DIR)
	mkdir -p $(FREETZ_MATTER_TARGET_DIR)/root
	$(call COPY_USING_TAR,$(FREETZ_MATTER_MAKE_DIR)/files,$(FREETZ_MATTER_TARGET_DIR))
	chmod 755 \
		$(FREETZ_MATTER_DEST_DIR)/etc/init.d/rc.freetz-matter \
		$(FREETZ_MATTER_DEST_DIR)/etc/default.freetz-matter/freetz-matter.save \
		$(FREETZ_MATTER_DEST_DIR)/usr/lib/cgi-bin/freetz-matter.cgi

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_STAGING_TARGET)

$(pkg)-clean:
	$(RM) -r $(FREETZ_MATTER_DIR)/target

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
