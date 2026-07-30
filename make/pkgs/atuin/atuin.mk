$(call PKG_INIT_BIN, 18.16.1)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v18.16.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=752802d4e8eef4896e9bc779b82f85e3d433c5934df5169e9b0f2537acf7f6e9
$(PKG)_SITE:=https://github.com/atuinsh/atuin/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/atuin-v18.16.1
### WEBSITE:=https://github.com/atuinsh/atuin
### CHANGES:=https://github.com/atuinsh/atuin/releases
### CVSREPO:=https://github.com/atuinsh/atuin

ATUIN_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
ATUIN_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
ATUIN_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
ATUIN_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(ATUIN_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
ATUIN_CARGO_HOME:=$(abspath $(ATUIN_DIR)/.cargo)
$(PKG)_BINARY:=$(ATUIN_DIR)/target/$(ATUIN_RUST_TARGET_DIR)/release/atuin
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/atuin

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(ATUIN_DIR)/.configured
	cd $(ATUIN_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(ATUIN_DIR))"; \
	export CARGO_HOME="$(ATUIN_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export XDG_CACHE_HOME="$(abspath $(ATUIN_DIR))/.cache"; \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie -C link-arg=-latomic"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-C", "link-arg=-latomic"]\n' \
		"$(ATUIN_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo fetch --locked --target "$(ATUIN_RUST_TARGET_ARG)"; \
	for socket2_src in $$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs; do \
		[ -f "$$socket2_src" ] || continue; \
		sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
	done; \
	for libc_uclibc_mod2 in $$CARGO_HOME/registry/src/*/libc-0.2.185/src/unix/linux_like/linux/uclibc/mod.rs; do \
		[ -f "$$libc_uclibc_mod2" ] || continue; \
		libc_x86_dir="$$(dirname "$$libc_uclibc_mod2")/x86"; \
		if [ ! -d "$$libc_x86_dir" ]; then \
			mkdir -p "$$libc_x86_dir"; \
			python3 -c "import base64,sys;content=base64.b64decode(sys.argv[1]).decode();open(sys.argv[2],chr(119)).write(content)" \
				'Ly8hIERlZmluaXRpb25zIGZvciB1Q2xpYmMgb24gMzItYml0IHg4NiBzeXN0ZW1zCgp1c2UgY3JhdGU6Om9mZjY0X3Q7CnVzZSBjcmF0ZTo6cHJlbHVkZTo6KjsKCnB1YiB0eXBlIGJsa2NudF90ID0gY19sb25nOwpwdWIgdHlwZSBibGtzaXplX3QgPSBjX2xvbmc7CnB1YiB0eXBlIGNsb2NrX3QgPSBjX2xvbmc7CnB1YiB0eXBlIGZzYmxrY250X3QgPSBjX3Vsb25nOwpwdWIgdHlwZSBmc2ZpbGNudF90ID0gY191bG9uZzsKcHViIHR5cGUgZnN3b3JkX3QgPSBjX2xvbmc7CnB1YiB0eXBlIGlub190ID0gY191bG9uZzsKcHViIHR5cGUgbmxpbmtfdCA9IGNfdWludDsKcHViIHR5cGUgb2ZmX3QgPSBjX2xvbmc7CnB1YiB0eXBlIHN0YXQ2NCA9IHN0YXQ7CnB1YiB0eXBlIHN1c2Vjb25kc190ID0gY19sb25nOwpwdWIgdHlwZSB0aW1lX3QgPSBjX2ludDsKcHViIHR5cGUgd2NoYXJfdCA9IGNfaW50OwpwdWIgdHlwZSBwdGhyZWFkX3QgPSBjX3Vsb25nOwoKcHViIHR5cGUgZnNibGtjbnQ2NF90ID0gdTY0OwpwdWIgdHlwZSBmc2ZpbGNudDY0X3QgPSB1NjQ7CnB1YiB0eXBlIF9fdTY0ID0gY191bG9uZ2xvbmc7CnB1YiB0eXBlIF9fczY0ID0gY19sb25nbG9uZzsKCnMhIHsKICAgIHB1YiBzdHJ1Y3QgaXBjX3Blcm0gewogICAgICAgIHB1YiBfX2tleTogY3JhdGU6OmtleV90LAogICAgICAgIHB1YiB1aWQ6IGNyYXRlOjp1aWRfdCwKICAgICAgICBwdWIgZ2lkOiBjcmF0ZTo6Z2lkX3QsCiAgICAgICAgcHViIGN1aWQ6IGNyYXRlOjp1aWRfdCwKICAgICAgICBwdWIgY2dpZDogY3JhdGU6OmdpZF90LAogICAgICAgIHB1YiBtb2RlOiBjX3VzaG9ydCwgLy8gcmVhZCAvIHdyaXRlCiAgICAgICAgX19wYWQxOiBQYWRkaW5nPGNfdXNob3J0PiwKICAgICAgICBwdWIgX19zZXE6IGNfdXNob3J0LAogICAgICAgIF9fcGFkMjogUGFkZGluZzxjX3VzaG9ydD4sCiAgICAgICAgX191bnVzZWQxOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIF9fdW51c2VkMjogUGFkZGluZzxjX3Vsb25nPiwKICAgIH0KCiAgICBwdWIgc3RydWN0IHB0aHJlYWRfYXR0cl90IHsKICAgICAgICBfX2RldGFjaHN0YXRlOiBjX2ludCwKICAgICAgICBfX3NjaGVkcG9saWN5OiBjX2ludCwKICAgICAgICBfX3NjaGVkcGFyYW06IF9fc2NoZWRfcGFyYW0sCiAgICAgICAgX19pbmhlcml0c2NoZWQ6IGNfaW50LAogICAgICAgIF9fc2NvcGU6IGNfaW50LAogICAgICAgIF9fZ3VhcmRzaXplOiBzaXplX3QsCiAgICAgICAgX19zdGFja2FkZHJfc2V0OiBjX2ludCwKICAgICAgICBfX3N0YWNrYWRkcjogKm11dCBjX3ZvaWQsIC8vIGJldHRlciBkb24ndCB1c2UgaXQKICAgICAgICBfX3N0YWNrc2l6ZTogc2l6ZV90LAogICAgfQoKICAgIHB1YiBzdHJ1Y3QgX19zY2hlZF9wYXJhbSB7CiAgICAgICAgX19zY2hlZF9wcmlvcml0eTogY19pbnQsCiAgICB9CgogICAgcHViIHN0cnVjdCBzaWdpbmZvX3QgewogICAgICAgIHNpX3NpZ25vOiBjX2ludCwgICAgICAgLy8gc2lnbmFsIG51bWJlcgogICAgICAgIHNpX2Vycm5vOiBjX2ludCwgICAgICAgLy8gaWYgbm90IHplcm86IGVycm9yIHZhbHVlIG9mIHNpZ25hbCwgc2VlIGVycm5vLgogICAgICAgIHNpX2NvZGU6IGNfaW50LCAgICAgICAgLy8gc2lnbmFsIGNvZGUKICAgICAgICBfcGFkOiBbY19pbnQ7IDI5XSwgICAgIC8vIHBhZGRpbmcgdG8gMTI4IGJ5dGVzCiAgICB9CgogICAgcHViIHN0cnVjdCBzaG1pZF9kcyB7CiAgICAgICAgcHViIHNobV9wZXJtOiBjcmF0ZTo6aXBjX3Blcm0sCiAgICAgICAgX19zaG1fcGFkMTogUGFkZGluZzxjX3Vsb25nPiwKICAgICAgICBwdWIgc2htX3NlZ3N6OiBzaXplX3QsCiAgICAgICAgX19zaG1fcGFkMjogUGFkZGluZzxjX3Vsb25nPiwKICAgICAgICBwdWIgc2htX2F0aW1lOiB0aW1lX3QsCiAgICAgICAgX19zaG1fcGFkMzogUGFkZGluZzxjX3Vsb25nPiwKICAgICAgICBwdWIgc2htX2R0aW1lOiB0aW1lX3QsCiAgICAgICAgX19zaG1fcGFkNDogUGFkZGluZzxjX3Vsb25nPiwKICAgICAgICBwdWIgc2htX2N0aW1lOiB0aW1lX3QsCiAgICAgICAgX19zaG1fcGFkNTogUGFkZGluZzxjX3Vsb25nPiwKICAgICAgICBwdWIgc2htX2NwaWQ6IGNyYXRlOjpwaWRfdCwKICAgICAgICBwdWIgc2htX2xwaWQ6IGNyYXRlOjpwaWRfdCwKICAgICAgICBwdWIgc2htX25hdHRjaDogY3JhdGU6OnNobWF0dF90LAogICAgICAgIF9fc2htX3BhZDY6IFBhZGRpbmc8Y191bG9uZz4sCiAgICAgICAgX191bnVzZWQxOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIF9fdW51c2VkMjogUGFkZGluZzxjX3Vsb25nPiwKICAgIH0KCiAgICBwdWIgc3RydWN0IG1zcWlkX2RzIHsKICAgICAgICBwdWIgbXNnX3Blcm06IGNyYXRlOjppcGNfcGVybSwKICAgICAgICBfX21zZ19wYWQxOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIHB1YiBtc2dfc3RpbWU6IHRpbWVfdCwKICAgICAgICBfX21zZ19wYWQyOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIHB1YiBtc2dfcnRpbWU6IHRpbWVfdCwKICAgICAgICBfX21zZ19wYWQzOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIHB1YiBtc2dfY3RpbWU6IHRpbWVfdCwKICAgICAgICBfX21zZ19wYWQ0OiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIF9fbXNnX2NiOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIF9fbXNnX3FudW06IFBhZGRpbmc8Y191bG9uZz4sCiAgICAgICAgX19tc2dfcWJ5dGVzOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIF9fbXNnX2xzcGlkOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgICAgIF9fbXNnX2xycGlkOiBQYWRkaW5nPGNfdWxvbmc+LAogICAgfQoKICAgIHB1YiBzdHJ1Y3Qgc29ja2FkZHIgewogICAgICAgIHB1YiBzYV9mYW1pbHk6IGNyYXRlOjpzYV9mYW1pbHlfdCwKICAgICAgICBwdWIgc2FfZGF0YTogW2NfY2hhcjsgMTRdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3Qgc29ja2FkZHJfaW4gewogICAgICAgIHB1YiBzaW5fZmFtaWx5OiBjcmF0ZTo6c2FfZmFtaWx5X3QsCiAgICAgICAgcHViIHNpbl9wb3J0OiBjcmF0ZTo6aW5fcG9ydF90LAogICAgICAgIHB1YiBzaW5fYWRkcjogY3JhdGU6OmluX2FkZHIsCiAgICAgICAgcHViIHNpbl96ZXJvOiBbdTg7IDhdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3Qgc29ja2FkZHJfaW42IHsKICAgICAgICBwdWIgc2luNl9mYW1pbHk6IGNyYXRlOjpzYV9mYW1pbHlfdCwKICAgICAgICBwdWIgc2luNl9wb3J0OiBjcmF0ZTo6aW5fcG9ydF90LAogICAgICAgIHB1YiBzaW42X2Zsb3dpbmZvOiB1MzIsCiAgICAgICAgcHViIHNpbjZfYWRkcjogY3JhdGU6OmluNl9hZGRyLAogICAgICAgIHB1YiBzaW42X3Njb3BlX2lkOiB1MzIsCiAgICB9CgogICAgcHViIHN0cnVjdCBzdGF0IHsKICAgICAgICBwdWIgc3RfZGV2OiBjcmF0ZTo6ZGV2X3QsCiAgICAgICAgX19wYWQxOiBQYWRkaW5nPGNfdXNob3J0PiwKICAgICAgICBwdWIgc3RfaW5vOiBjcmF0ZTo6aW5vX3QsCiAgICAgICAgcHViIHN0X21vZGU6IGNyYXRlOjptb2RlX3QsCiAgICAgICAgcHViIHN0X25saW5rOiBjcmF0ZTo6bmxpbmtfdCwKICAgICAgICBwdWIgc3RfdWlkOiBjcmF0ZTo6dWlkX3QsCiAgICAgICAgcHViIHN0X2dpZDogY3JhdGU6OmdpZF90LAogICAgICAgIHB1YiBzdF9yZGV2OiBjcmF0ZTo6ZGV2X3QsCiAgICAgICAgX19wYWQyOiBQYWRkaW5nPGNfdXNob3J0PiwKICAgICAgICBwdWIgc3Rfc2l6ZTogb2ZmNjRfdCwKICAgICAgICBwdWIgc3RfYmxrc2l6ZTogY3JhdGU6OmJsa3NpemVfdCwKICAgICAgICBwdWIgc3RfYmxvY2tzOiBjcmF0ZTo6YmxrY250NjRfdCwKICAgICAgICBwdWIgc3RfYXRpbWU6IHRpbWVfdCwKICAgICAgICBwdWIgc3RfYXRpbWVfbnNlYzogY19sb25nLAogICAgICAgIHB1YiBzdF9tdGltZTogdGltZV90LAogICAgICAgIHB1YiBzdF9tdGltZV9uc2VjOiBjX2xvbmcsCiAgICAgICAgcHViIHN0X2N0aW1lOiB0aW1lX3QsCiAgICAgICAgcHViIHN0X2N0aW1lX25zZWM6IGNfbG9uZywKICAgICAgICBfX3VudXNlZDQ6IFBhZGRpbmc8Y19sb25nPiwKICAgICAgICBfX3VudXNlZDU6IFBhZGRpbmc8Y19sb25nPiwKICAgIH0KCiAgICBwdWIgc3RydWN0IHNpZ2FjdGlvbiB7CiAgICAgICAgcHViIHNhX2hhbmRsZXI6IGNyYXRlOjpzaWdoYW5kbGVyX3QsCiAgICAgICAgcHViIHNhX21hc2s6IGNyYXRlOjpzaWdzZXRfdCwKICAgICAgICBwdWIgc2FfZmxhZ3M6IGNfaW50LAogICAgICAgIHB1YiBzYV9yZXN0b3JlcjogT3B0aW9uPGV4dGVybiAiQyIgZm4oKT4sCiAgICB9CgogICAgcHViIHN0cnVjdCBzdGFja190IHsKICAgICAgICBwdWIgc3Nfc3A6ICptdXQgY192b2lkLAogICAgICAgIHB1YiBzc19mbGFnczogY19pbnQsCiAgICAgICAgcHViIHNzX3NpemU6IHNpemVfdCwKICAgIH0KCiAgICBwdWIgc3RydWN0IHN0YXRmcyB7CiAgICAgICAgcHViIGZfdHlwZTogY19sb25nLAogICAgICAgIHB1YiBmX2JzaXplOiBjX2xvbmcsCiAgICAgICAgcHViIGZfYmxvY2tzOiBjcmF0ZTo6ZnNibGtjbnRfdCwKICAgICAgICBwdWIgZl9iZnJlZTogY3JhdGU6OmZzYmxrY250X3QsCiAgICAgICAgcHViIGZfYmF2YWlsOiBjcmF0ZTo6ZnNibGtjbnRfdCwKICAgICAgICBwdWIgZl9maWxlczogY3JhdGU6OmZzZmlsY250X3QsCiAgICAgICAgcHViIGZfZmZyZWU6IGNyYXRlOjpmc2ZpbGNudF90LAogICAgICAgIHB1YiBmX2ZzaWQ6IGNyYXRlOjpmc2lkX3QsCiAgICAgICAgcHViIGZfbmFtZWxlbjogY19sb25nLAogICAgICAgIHB1YiBmX2Zyc2l6ZTogY19sb25nLAogICAgICAgIHB1YiBmX2ZsYWdzOiBjX2xvbmcsCiAgICAgICAgcHViIGZfc3BhcmU6IFtjX2xvbmc7IDRdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3Qgc3RhdGZzNjQgewogICAgICAgIHB1YiBmX3R5cGU6IGNfbG9uZywKICAgICAgICBwdWIgZl9ic2l6ZTogY19sb25nLAogICAgICAgIHB1YiBmX2Jsb2NrczogdTY0LAogICAgICAgIHB1YiBmX2JmcmVlOiB1NjQsCiAgICAgICAgcHViIGZfYmF2YWlsOiB1NjQsCiAgICAgICAgcHViIGZfZmlsZXM6IHU2NCwKICAgICAgICBwdWIgZl9mZnJlZTogdTY0LAogICAgICAgIHB1YiBmX2ZzaWQ6IGNyYXRlOjpmc2lkX3QsCiAgICAgICAgcHViIGZfbmFtZWxlbjogY19sb25nLAogICAgICAgIHB1YiBmX2Zyc2l6ZTogY19sb25nLAogICAgICAgIHB1YiBmX2ZsYWdzOiBjX2xvbmcsCiAgICAgICAgcHViIGZfc3BhcmU6IFtjX2xvbmc7IDRdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3Qgc3RhdHZmczY0IHsKICAgICAgICBwdWIgZl90eXBlOiBjX3Vsb25nLAogICAgICAgIHB1YiBmX2JzaXplOiBjX3Vsb25nLAogICAgICAgIHB1YiBmX2Jsb2NrczogdTY0LAogICAgICAgIHB1YiBmX2JmcmVlOiB1NjQsCiAgICAgICAgcHViIGZfYmF2YWlsOiB1NjQsCiAgICAgICAgcHViIGZfZmlsZXM6IHU2NCwKICAgICAgICBwdWIgZl9mZnJlZTogdTY0LAogICAgICAgIHB1YiBmX2ZzaWQ6IGNfdWxvbmcsCiAgICAgICAgcHViIGZfbmFtZWxlbjogY191bG9uZywKICAgICAgICBwdWIgZl9mcnNpemU6IGNfdWxvbmcsCiAgICAgICAgcHViIGZfZmxhZ3M6IGNfdWxvbmcsCiAgICAgICAgcHViIGZfc3BhcmU6IFtjX3Vsb25nOyA0XSwKICAgIH0KCiAgICBwdWIgc3RydWN0IG1zZ2hkciB7CiAgICAgICAgcHViIG1zZ19uYW1lOiAqbXV0IGNfdm9pZCwKICAgICAgICBwdWIgbXNnX25hbWVsZW46IGNyYXRlOjpzb2NrbGVuX3QsCiAgICAgICAgcHViIG1zZ19pb3Y6ICptdXQgY3JhdGU6OmlvdmVjLAogICAgICAgIHB1YiBtc2dfaW92bGVuOiBjX2ludCwKICAgICAgICBwdWIgbXNnX2NvbnRyb2w6ICptdXQgY192b2lkLAogICAgICAgIHB1YiBtc2dfY29udHJvbGxlbjogY3JhdGU6OnNvY2tsZW5fdCwKICAgICAgICBwdWIgbXNnX2ZsYWdzOiBjX2ludCwKICAgIH0KCiAgICBwdWIgc3RydWN0IHRlcm1pb3MgewogICAgICAgIHB1YiBjX2lmbGFnOiBjcmF0ZTo6dGNmbGFnX3QsCiAgICAgICAgcHViIGNfb2ZsYWc6IGNyYXRlOjp0Y2ZsYWdfdCwKICAgICAgICBwdWIgY19jZmxhZzogY3JhdGU6OnRjZmxhZ190LAogICAgICAgIHB1YiBjX2xmbGFnOiBjcmF0ZTo6dGNmbGFnX3QsCiAgICAgICAgcHViIGNfbGluZTogY3JhdGU6OmNjX3QsCiAgICAgICAgcHViIGNfY2M6IFtjcmF0ZTo6Y2NfdDsgY3JhdGU6Ok5DQ1NdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3Qgc2lnc2V0X3QgewogICAgICAgIF9fdmFsOiBbY191bG9uZzsgMzJdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3Qgc3lzaW5mbyB7CiAgICAgICAgcHViIHVwdGltZTogY19sb25nLAogICAgICAgIHB1YiBsb2FkczogW2NfdWxvbmc7IDNdLAogICAgICAgIHB1YiB0b3RhbHJhbTogY191bG9uZywKICAgICAgICBwdWIgZnJlZXJhbTogY191bG9uZywKICAgICAgICBwdWIgc2hhcmVkcmFtOiBjX3Vsb25nLAogICAgICAgIHB1YiBidWZmZXJyYW06IGNfdWxvbmcsCiAgICAgICAgcHViIHRvdGFsc3dhcDogY191bG9uZywKICAgICAgICBwdWIgZnJlZXN3YXA6IGNfdWxvbmcsCiAgICAgICAgcHViIHByb2NzOiBjX3VzaG9ydCwKICAgICAgICBwdWIgcGFkOiBjX3VzaG9ydCwKICAgICAgICBwdWIgdG90YWxoaWdoOiBjX3Vsb25nLAogICAgICAgIHB1YiBmcmVlaGlnaDogY191bG9uZywKICAgICAgICBwdWIgbWVtX3VuaXQ6IGNfdWludCwKICAgICAgICBwdWIgX2Y6IFtjX2NoYXI7IDBdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3QgZ2xvYl90IHsKICAgICAgICBwdWIgZ2xfcGF0aGM6IHNpemVfdCwKICAgICAgICBwdWIgZ2xfcGF0aHY6ICptdXQgKm11dCBjX2NoYXIsCiAgICAgICAgcHViIGdsX29mZnM6IHNpemVfdCwKICAgICAgICBwdWIgZ2xfZmxhZ3M6IGNfaW50LAogICAgICAgIF9fdW51c2VkMTogUGFkZGluZzwqbXV0IGNfdm9pZD4sCiAgICAgICAgX191bnVzZWQyOiBQYWRkaW5nPCptdXQgY192b2lkPiwKICAgICAgICBfX3VudXNlZDM6IFBhZGRpbmc8Km11dCBjX3ZvaWQ+LAogICAgICAgIF9fdW51c2VkNDogUGFkZGluZzwqbXV0IGNfdm9pZD4sCiAgICAgICAgX191bnVzZWQ1OiBQYWRkaW5nPCptdXQgY192b2lkPiwKICAgIH0KCiAgICBwdWIgc3RydWN0IGNwdV9zZXRfdCB7CiAgICAgICAgYml0czogW3UzMjsgMzJdLAogICAgfQoKICAgIHB1YiBzdHJ1Y3QgZnNpZF90IHsKICAgICAgICBfX3ZhbDogW2NfaW50OyAyXSwKICAgIH0KCiAgICBwdWIgc3RydWN0IHNlbV90IHsKICAgICAgICBfX3NpemU6IFtjX2NoYXI7IDE2XSwKICAgICAgICBfX2FsaWduOiBbY19sb25nOyAwXSwKICAgIH0KCiAgICBwdWIgc3RydWN0IGNtc2doZHIgewogICAgICAgIHB1YiBjbXNnX2xlbjogc2l6ZV90LAogICAgICAgIHB1YiBjbXNnX2xldmVsOiBjX2ludCwKICAgICAgICBwdWIgY21zZ190eXBlOiBjX2ludCwKICAgIH0KfQoKc19ub19leHRyYV90cmFpdHMhIHsKICAgIHB1YiBzdHJ1Y3QgZGlyZW50IHsKICAgICAgICBwdWIgZF9pbm86IGNyYXRlOjppbm9fdCwKICAgICAgICBwdWIgZF9vZmY6IG9mZjY0X3QsCiAgICAgICAgcHViIGRfcmVjbGVuOiBjX3VzaG9ydCwKICAgICAgICBwdWIgZF90eXBlOiBjX3VjaGFyLAogICAgICAgIHB1YiBkX25hbWU6IFtjX2NoYXI7IDI1Nl0sCiAgICB9Cn0K' "$$libc_x86_dir/mod.rs"; \
		fi; \
		perl -0pi -e 's@(    } else if #\[cfg\(target_arch = "x86_64"\)\] \{
        mod x86_64;
        pub use self::x86_64::\*;
    } else if #\[cfg\(target_arch = "arm"\)])@    } else if #[cfg(target_arch = "x86")] {
        mod x86;
        pub use self::x86::*;
    } else if #[cfg(target_arch = "x86_64")] {
        mod x86_64;
        pub use self::x86_64::*;
    } else if #[cfg(target_arch = "arm")]@s' "$$libc_uclibc_mod2"; \
	done; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	for libc_uclibc_mod in $$HOME/.cargo/registry/src/*/libc-0.2.183/src/unix/linux_like/linux/uclibc/mod.rs; do \
		[ -f "$$libc_uclibc_mod" ] || continue; \
		if ! grep -q 'MFD_HUGE_1MB' "$$libc_uclibc_mod"; then \
			perl -0pi -e 's@(pub const MAP_HUGE_16GB: c_int = 34 << MAP_HUGE_SHIFT;)@$$1\n\n// MFD_HUGE constants (from linux_l4re_shared, missing on uClibc)\npub const MFD_HUGETLB: c_uint = 0x0004;\npub const MFD_HUGE_64KB: c_uint = 0x40000000;\npub const MFD_HUGE_512KB: c_uint = 0x4c000000;\npub const MFD_HUGE_1MB: c_uint = 0x50000000;\npub const MFD_HUGE_2MB: c_uint = 0x54000000;\npub const MFD_HUGE_8MB: c_uint = 0x5c000000;\npub const MFD_HUGE_16MB: c_uint = 0x60000000;\npub const MFD_HUGE_32MB: c_uint = 0x64000000;\npub const MFD_HUGE_256MB: c_uint = 0x70000000;\npub const MFD_HUGE_512MB: c_uint = 0x74000000;\npub const MFD_HUGE_1GB: c_uint = 0x78000000;\npub const MFD_HUGE_2GB: c_uint = 0x7c000000;\npub const MFD_HUGE_16GB: c_uint = 0x88000000;\npub const MFD_HUGE_MASK: c_uint = 63;\npub const MFD_HUGE_SHIFT: c_uint = 26;@s' "$$libc_uclibc_mod"; \
		fi; \
	done; \
	for boxcar_src in $$HOME/.cargo/registry/src/*/boxcar-*/src/lib.rs; do \
		[ -f "$$boxcar_src" ] || continue; \
		if ! grep -q 'Freetz 32-bit AtomicU64 fallback' "$$boxcar_src"; then \
			perl -0pi -e 's@(use std::sync::atomic::\{AtomicBool, AtomicPtr, AtomicU64, Ordering\};)@// Freetz 32-bit AtomicU64 fallback for targets without native 64-bit atomics.\n#[cfg(target_has_atomic = "64")]\nuse std::sync::atomic::{AtomicBool, AtomicPtr, AtomicU64, Ordering};\n#[cfg(not(target_has_atomic = "64"))]\nuse std::sync::{atomic::{AtomicBool, AtomicPtr, Ordering}, Mutex};\n\n#[cfg(not(target_has_atomic = "64"))]\n#[derive(Debug)]\nstruct AtomicU64(Mutex<u64>);\n\n#[cfg(not(target_has_atomic = "64"))]\nimpl AtomicU64 {\n    fn new(val: u64) -> Self { Self(Mutex::new(val)) }\n    fn load(&self, _: Ordering) -> u64 { *self.0.lock().unwrap() }\n    fn store(&self, val: u64, _: Ordering) { *self.0.lock().unwrap() = val; }\n    fn fetch_add(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock += val; prev }\n    fn fetch_or(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock |= val; prev }\n    fn into_inner(self) -> u64 { self.0.into_inner().unwrap() }\n}@s' "$$boxcar_src"; \
		fi; \
	done; \
	for atuin_boxcar_src in $$HOME/crates/atuin-nucleo/src/boxcar.rs; do \
		[ -f "$$atuin_boxcar_src" ] || continue; \
		if ! grep -q 'Freetz 32-bit AtomicU64 fallback' "$$atuin_boxcar_src"; then \
			perl -0pi -e 's@(use std::sync::atomic::\{AtomicBool, AtomicPtr, AtomicU64, Ordering\};)@// Freetz 32-bit AtomicU64 fallback for targets without native 64-bit atomics.\n#[cfg(target_has_atomic = "64")]\nuse std::sync::atomic::{AtomicBool, AtomicPtr, AtomicU64, Ordering};\n#[cfg(not(target_has_atomic = "64"))]\nuse std::sync::{atomic::{AtomicBool, AtomicPtr, Ordering}, Mutex};\n\n#[cfg(not(target_has_atomic = "64"))]\n#[derive(Debug)]\nstruct AtomicU64(Mutex<u64>);\n\n#[cfg(not(target_has_atomic = "64"))]\nimpl AtomicU64 {\n    fn new(val: u64) -> Self { Self(Mutex::new(val)) }\n    fn load(&self, _: Ordering) -> u64 { *self.0.lock().unwrap() }\n    fn store(&self, val: u64, _: Ordering) { *self.0.lock().unwrap() = val; }\n    fn fetch_add(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock += val; prev }\n    fn fetch_or(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock |= val; prev }\n    fn into_inner(self) -> u64 { self.0.into_inner().unwrap() }\n}@s' "$$atuin_boxcar_src"; \
		fi; \
	done; \
	$(ATUIN_CARGO_BUILD_CMD) --target "$(ATUIN_RUST_TARGET_ARG)" --bin atuin || CARGO_BUILD_JOBS=1 $(ATUIN_CARGO_BUILD_CMD) --target "$(ATUIN_RUST_TARGET_ARG)" --bin atuin

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg): $($(PKG)_TARGET_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ATUIN_DIR) clean
	$(RM) $($(PKG)_BINARY) $(ATUIN_DIR)/.configured $(ATUIN_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
