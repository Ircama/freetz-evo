$(call TOOLS_INIT, 1.0.0)
### WEBSITE:=https://www.rust-lang.org/
### MANPAGE:=https://doc.rust-lang.org/
### CHANGES:=https://github.com/rust-lang/rust/releases
### CVSREPO:=https://github.com/rust-lang/rust

RUST_HOST_TARGET_DIR:=$(HOST_TOOLS_DIR)/usr/bin
RUST_HOST_TARGET_BINARY:=$(RUST_HOST_TARGET_DIR)/rustc

$(TOOLS_CONFIGURED_NOP)


$(RUST_HOST_TARGET_BINARY): | $(HOST_TOOLS_DIR)
	@if ! command -v rustc >/dev/null 2>&1; then \
		echo "ERROR: rustc not found on host PATH"; \
		exit 1; \
	fi
	@if ! command -v cargo >/dev/null 2>&1; then \
		echo "ERROR: cargo not found on host PATH"; \
		exit 1; \
	fi
	@mkdir -p $(RUST_HOST_TARGET_DIR)
	ln -sf "$$(command -v rustc)" $(RUST_HOST_TARGET_DIR)/rustc
	ln -sf "$$(command -v cargo)" $(RUST_HOST_TARGET_DIR)/cargo
	@touch -c $@

$(pkg)-precompiled: $(RUST_HOST_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(RUST_HOST_TARGET_DIR)/rustc $(RUST_HOST_TARGET_DIR)/cargo

$(pkg)-dirclean:
	$(RM) $(RUST_HOST_TARGET_DIR)/rustc $(RUST_HOST_TARGET_DIR)/cargo

$(pkg)-distclean: $(pkg)-dirclean
	$(RM) $(RUST_HOST_TARGET_DIR)/rustc $(RUST_HOST_TARGET_DIR)/cargo

$(TOOLS_FINISH)
