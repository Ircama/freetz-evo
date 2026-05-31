$(call TOOLS_INIT, 1.0.0)
### WEBSITE:=https://www.rust-lang.org/
### MANPAGE:=https://doc.rust-lang.org/
### CHANGES:=https://github.com/rust-lang/rust/releases
### CVSREPO:=https://github.com/rust-lang/rust

RUST_HOST_TARGET_DIR:=$(HOST_TOOLS_DIR)/usr/bin
RUST_HOST_TARGET_BINARY:=$(RUST_HOST_TARGET_DIR)/rustc

$(TOOLS_CONFIGURED_NOP)


$(RUST_HOST_TARGET_BINARY): | $(HOST_TOOLS_DIR)
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
