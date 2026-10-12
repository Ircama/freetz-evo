# matter-bridge -- native Matter WebSocket server for Domoticz (no Node.js).
#
# The C++ sources of this package live in its src/ directory in the repository
# and are copied into the package source directory under source/ before the
# build, because freetz removes $(PKG)_DIR while preparing a package (setting
# $(PKG)_DIR to the repository directory would delete the package itself).
# Same pattern as the ariang package.
$(call PKG_INIT_BIN, 0.1)
### STEWARD:=Ircama
$(PKG)_CATEGORY_PKGS:=Home Automation

$(PKG)_BUILD_DIR:=$($(PKG)_DIR)/freetz-build
$(PKG)_BINARY:=$($(PKG)_BUILD_DIR)/matter-bridge
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/matter-bridge

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_MATTER_BRIDGE

# ---------------------------------------------------------------------------
# matter-bridge-ctl -- milestone 2: the native Matter controller (rs-matter).
#
# Second binary of the same package. rs-matter and its revision are the same
# ones the freetz-matter package is verified against; keep the rev in sync with
# controller/Cargo.toml.
# ---------------------------------------------------------------------------
FREETZ_MATTER_BRIDGE_RS_MATTER_REV:=7d5684f495fe5bca03d993647543508ab7587f10

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
$(PKG)_CTL_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/matter-bridge-ctl

$(PKG)_BINARY:=$($(PKG)_DIR)/controller/target/$($(PKG)_RUST_TARGET_DIR)/release/matter-bridge
$(PKG)_CTL_BINARY:=$($(PKG)_DIR)/controller/target/$($(PKG)_RUST_TARGET_DIR)/release/matter-bridge-ctl
$(PKG)_CARGO_HOME:=$(abspath $($(PKG)_DIR)/controller/.cargo)
$(eval $(call RUST_DEPENDS_VARS))

# This package has no tarball to download: the sources are copied from the
# package directory into the (freetz owned) source directory.
$($(PKG)_DIR)/.unpacked: $(MATTER_BRIDGE_MAKE_DIR)/src/matter-bridge.cpp \
		$(MATTER_BRIDGE_MAKE_DIR)/controller/Cargo.toml \
		$(MATTER_BRIDGE_MAKE_DIR)/controller/Cargo.lock \
		$(wildcard $(MATTER_BRIDGE_MAKE_DIR)/controller/src/*.rs) | $(SOURCE_DIR)
	@$(call _ECHO,preparing)
	mkdir -p $(MATTER_BRIDGE_DIR)/src $(MATTER_BRIDGE_DIR)/controller/src
	cp $(MATTER_BRIDGE_MAKE_DIR)/src/matter-bridge.cpp $(MATTER_BRIDGE_DIR)/src/
	cp $(MATTER_BRIDGE_MAKE_DIR)/controller/Cargo.toml $(MATTER_BRIDGE_DIR)/controller/
	cp $(MATTER_BRIDGE_MAKE_DIR)/controller/Cargo.lock $(MATTER_BRIDGE_DIR)/controller/
	cp $(MATTER_BRIDGE_MAKE_DIR)/controller/src/*.rs $(MATTER_BRIDGE_DIR)/controller/src/
	@touch $@

$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

# Same serialization as freetz-matter: rs-matter's IDL codegen emits ~30 MB of
# Rust and a single rustc job already peaks at ~5.6 GB RSS, so one cargo job and
# one rustc thread are used on purpose.
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	@$(call _ECHO,building)
	cd $(MATTER_BRIDGE_DIR)/controller; \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(MATTER_BRIDGE_DIR)/controller)"; \
	export CARGO_HOME="$(MATTER_BRIDGE_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-Zthreads=1"]\n' \
		"$(MATTER_BRIDGE_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	export CARGO_BUILD_JOBS=1; \
	cargo +nightly fetch --locked --target "$(MATTER_BRIDGE_RUST_TARGET_DIR)" && \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT,1.1.5) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.3) \
	cargo +nightly build --locked --release $(MATTER_BRIDGE_CARGO_BUILD_STD_FLAGS) \
		--target "$(MATTER_BRIDGE_RUST_TARGET_ARG)"

$($(PKG)_CTL_BINARY): $($(PKG)_BINARY)
	@test -x $@

$($(PKG)_CTL_TARGET_BINARY): $($(PKG)_CTL_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg): $($(PKG)_BINARY) $($(PKG)_CTL_BINARY)

$($(PKG)_DEST_DIR)/usr/bin/matter-bridge-setup: $(MATTER_BRIDGE_MAKE_DIR)/files/root/usr/bin/matter-bridge-setup
	mkdir -p $(dir $@)
	cp $< $@
	chmod 755 $@

# Web interface page (Freetz menu entry "Matter bridge (Domoticz)")
$($(PKG)_DEST_DIR)/usr/lib/cgi-bin/matter-bridge.cgi: $(MATTER_BRIDGE_MAKE_DIR)/files/root/usr/lib/cgi-bin/matter-bridge.cgi
	mkdir -p $(dir $@)
	cp $< $@
	chmod 755 $@

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $($(PKG)_CTL_TARGET_BINARY) $($(PKG)_DEST_DIR)/usr/bin/matter-bridge-setup $($(PKG)_DEST_DIR)/usr/lib/cgi-bin/matter-bridge.cgi

$(pkg)-clean:
	$(RM) -r $(MATTER_BRIDGE_BUILD_DIR) $(MATTER_BRIDGE_DIR)/controller/target

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY) $($(PKG)_CTL_TARGET_BINARY)

$(PKG_FINISH)
