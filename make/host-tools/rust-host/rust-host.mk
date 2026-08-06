$(call TOOLS_INIT, 1.0.0)
### WEBSITE:=https://www.rust-lang.org/
### MANPAGE:=https://doc.rust-lang.org/
### CHANGES:=https://github.com/rust-lang/rust/releases
### CVSREPO:=https://github.com/rust-lang/rust

RUST_HOST_TARGET_DIR:=$(HOST_TOOLS_DIR)/usr/bin
RUST_HOST_TARGET_BINARY:=$(RUST_HOST_TARGET_DIR)/rustc

# Custom Rust target spec files (e.g. i686-unknown-linux-uclibc.json) must live
# under $(FREETZ_BASE_DIR)/toolchain/rust/targets/, but the whole /toolchain
# directory is gitignored, so those files get lost on a clean checkout and every
# cargo invocation fails with "target path ... is not a valid file". Keep the
# canonical copies tracked in make/include/rust/ and re-materialize them here:
# rust-host is a prerequisite of every Rust package, so this runs before any
# cargo build. Safe on mips/arm (builtin targets): FREETZ_TARGET_RUST_CUSTOM_TARGET
# is empty there, so both the rule and the prerequisite expand to nothing.
RUST_TARGET_SPEC_CUSTOM:=$(call qstrip,$(FREETZ_TARGET_RUST_CUSTOM_TARGET))
RUST_TARGET_SPEC_SRC:=$(if $(RUST_TARGET_SPEC_CUSTOM),$(FREETZ_BASE_DIR)/make/include/rust/$(RUST_TARGET_SPEC_CUSTOM))
RUST_TARGET_SPEC_DST:=$(if $(RUST_TARGET_SPEC_CUSTOM),$(FREETZ_BASE_DIR)/toolchain/rust/targets/$(RUST_TARGET_SPEC_CUSTOM))

ifneq ($(RUST_TARGET_SPEC_DST),)
$(FREETZ_BASE_DIR)/toolchain/rust/targets/%.json: $(FREETZ_BASE_DIR)/make/include/rust/%.json
	@mkdir -p $(dir $@)
	@cp -f $< $@
	@echo "Re-materialized Rust target spec: $@"
endif

$(TOOLS_CONFIGURED_NOP)


$(RUST_HOST_TARGET_BINARY): $(RUST_TARGET_SPEC_DST) | $(HOST_TOOLS_DIR)
	@rustc_bin="$$(command -v rustc 2>/dev/null || true)"; \
	[ -n "$$rustc_bin" ] || [ ! -x "$$HOME/.cargo/bin/rustc" ] || rustc_bin="$$HOME/.cargo/bin/rustc"; \
	if [ -z "$$rustc_bin" ]; then \
		echo "ERROR: rustc not found on host PATH or in $$HOME/.cargo/bin"; \
		exit 1; \
	fi; \
	cargo_bin="$$(command -v cargo 2>/dev/null || true)"; \
	[ -n "$$cargo_bin" ] || [ ! -x "$$HOME/.cargo/bin/cargo" ] || cargo_bin="$$HOME/.cargo/bin/cargo"; \
	if [ -z "$$cargo_bin" ]; then \
		echo "ERROR: cargo not found on host PATH or in $$HOME/.cargo/bin"; \
		exit 1; \
	fi; \
	mkdir -p $(RUST_HOST_TARGET_DIR); \
	ln -sf "$$rustc_bin" $(RUST_HOST_TARGET_DIR)/rustc; \
	ln -sf "$$cargo_bin" $(RUST_HOST_TARGET_DIR)/cargo

$(pkg)-precompiled: $(RUST_HOST_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(RUST_HOST_TARGET_DIR)/rustc $(RUST_HOST_TARGET_DIR)/cargo

$(pkg)-dirclean:
	$(RM) $(RUST_HOST_TARGET_DIR)/rustc $(RUST_HOST_TARGET_DIR)/cargo

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(RUST_HOST_TARGET_DIR)/rustc $(RUST_HOST_TARGET_DIR)/cargo

$(TOOLS_FINISH)
