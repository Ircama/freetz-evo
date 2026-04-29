$(call PKG_INIT_BIN, 3.5.0)
$(PKG)_SOURCE:=amutorrent-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=4225e0fd786d703f60c68fb4f4dd66ceb74d27dabf123b02ccb9ef8b20f7164e
$(PKG)_SITE:=https://github.com/got3nks/amutorrent/archive/refs/tags
$(PKG)_TARBALL_STRIP_COMPONENTS := 1
### WEBSITE:=https://github.com/got3nks/amutorrent
### CHANGES:=https://github.com/got3nks/amutorrent/releases
### CVSREPO:=https://github.com/got3nks/amutorrent
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += nodejs python3-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_NODEJS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ENDIANNESS_DEPENDENT
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_MIPS
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_ARM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_AARCH64
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_ARCH_X86
$(PKG)_REBUILD_SUBOPTS += FREETZ_GCC_FLOAT_ABI
$(PKG)_REBUILD_SUBOPTS += FREETZ_GCC_FPU

AMUTORRENT_NODE_ARCH := $(or \
	$(if $(FREETZ_TARGET_ARCH_AARCH64),arm64), \
	$(if $(FREETZ_TARGET_ARCH_ARM),arm), \
	$(if $(FREETZ_TARGET_ARCH_MIPS),$(if $(FREETZ_TARGET_ARCH_LE),mipsel,mips)), \
	$(if $(FREETZ_TARGET_ARCH_X86),ia32) \
)

ifneq ($(strip $(FREETZ_PACKAGE_AMUTORRENT)$(filter amutorrent%,$(MAKECMDGOALS))),)
ifeq ($(strip $(AMUTORRENT_NODE_ARCH)),)
$(error amutorrent: unsupported target architecture for Node.js runtime)
endif
endif

AMUTORRENT_HOST_PYTHON := $(HOST_TOOLS_DIR)/usr/bin/python3
AMUTORRENT_HOST_ENV = \
	PATH="$(HOST_TOOLS_DIR)/usr/bin:$(PATH)" \
	HOME="$(AMUTORRENT_DIR)/.npm-home" \
	npm_config_cache="$(AMUTORRENT_DIR)/.npm-cache"
AMUTORRENT_SERVER_ENV = \
	$(AMUTORRENT_HOST_ENV) \
	PYTHON="$(AMUTORRENT_HOST_PYTHON)" \
	npm_config_python="$(AMUTORRENT_HOST_PYTHON)" \
	npm_config_nodedir="$(NODEJS_DIR)" \
	npm_config_target="$(NODEJS_VERSION)" \
	npm_config_platform="linux" \
	npm_config_arch="$(AMUTORRENT_NODE_ARCH)" \
	npm_config_target_arch="$(AMUTORRENT_NODE_ARCH)" \
	npm_config_build_from_source="true" \
	npm_config_update_binary="false" \
	CC="$(TARGET_CC)" \
	CXX="$(TARGET_CXX)" \
	AR="$(TARGET_AR)" \
	LD="$(TARGET_CC)" \
	RANLIB="$(TARGET_RANLIB)" \
	STRIP="$(TARGET_STRIP)" \
	CFLAGS="$(TARGET_CFLAGS)" \
	CXXFLAGS="$(TARGET_CXXFLAGS)" \
	CPPFLAGS="$(TARGET_CPPFLAGS)" \
	LDFLAGS="$(TARGET_LDFLAGS)"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_DIR)/.frontend-built: $($(PKG)_DIR)/.configured
	mkdir -p $(AMUTORRENT_DIR)/.npm-home $(AMUTORRENT_DIR)/.npm-cache
	cd $(AMUTORRENT_DIR) && rm -rf node_modules static/dist static/output.css
	cd $(AMUTORRENT_DIR) && env $(AMUTORRENT_HOST_ENV) /bin/sh -c 'if [ -f package-lock.json ]; then npm ci; else npm install; fi'
	cd $(AMUTORRENT_DIR) && env $(AMUTORRENT_HOST_ENV) npm run build
	[ -f $(AMUTORRENT_DIR)/static/output.css ]
	[ -d $(AMUTORRENT_DIR)/static/dist ]
	@touch $@

$($(PKG)_DIR)/.server-built: $($(PKG)_DIR)/.configured $(NODEJS_DIR)/.configured
	mkdir -p $(AMUTORRENT_DIR)/.npm-home $(AMUTORRENT_DIR)/.npm-cache
	cd $(AMUTORRENT_DIR)/server && rm -rf node_modules
	cd $(AMUTORRENT_DIR)/server && env $(AMUTORRENT_SERVER_ENV) /bin/sh -c 'if [ -f package-lock.json ]; then npm ci --omit=dev; else npm install --omit=dev; fi'
	[ -d $(AMUTORRENT_DIR)/server/node_modules ]
	@touch $@

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.frontend-built $($(PKG)_DIR)/.server-built
	[ -f $(AMUTORRENT_DIR)/static/output.css ]
	[ -d $(AMUTORRENT_DIR)/static/dist ]
	[ -d $(AMUTORRENT_DIR)/server/node_modules ]
	$(RM) -r $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent $(AMUTORRENT_DEST_DIR)/usr/mww/amutorrent
	mkdir -p $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/static
	mkdir -p $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/server
	cd $(AMUTORRENT_DIR) && tar cf - CHANGELOG.md scripts | (cd $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent && tar xf -)
	cd $(AMUTORRENT_DIR)/static && tar cf - index.html output.css dist service-icons flags | (cd $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/static && tar xf -)
	cd $(AMUTORRENT_DIR)/static && for asset in *.png *.ico *.svg site.webmanifest; do \
		[ -e "$$asset" ] || continue; \
		cp -a "$$asset" $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/static/; \
	done
	cd $(AMUTORRENT_DIR)/server && tar cf - server.js database.js lib middleware modules node_modules package.json package-lock.json | (cd $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/server && tar xf -)
	rm -rf $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/server/data $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/server/logs
	ln -snf /mod/etc/amutorrent/data $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/server/data
	ln -snf /mod/etc/amutorrent/logs $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/server/logs
	find $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent/scripts -type f -name '*.sh' -exec chmod 755 {} + 2>/dev/null || true
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.compiled

$(pkg)-clean:
	$(RM) -r $(AMUTORRENT_DIR)/node_modules
	$(RM) -r $(AMUTORRENT_DIR)/server/node_modules
	$(RM) -r $(AMUTORRENT_DIR)/static/dist
	$(RM) -f $(AMUTORRENT_DIR)/static/output.css
	$(RM) -r $(AMUTORRENT_DIR)/.npm-home $(AMUTORRENT_DIR)/.npm-cache
	$(RM) -f $($(PKG)_DIR)/.frontend-built $($(PKG)_DIR)/.server-built
	$(RM) -r $(AMUTORRENT_DIR)

$(pkg)-uninstall:
	$(RM) -r $(AMUTORRENT_DEST_DIR)/usr/lib/amutorrent
	$(RM) -r $(AMUTORRENT_DEST_DIR)/usr/mww/amutorrent
	$(RM) -f $(AMUTORRENT_DEST_DIR)/usr/lib/cgi-bin/amutorrent.cgi
	$(RM) -f $(AMUTORRENT_DEST_DIR)/etc/init.d/rc.amutorrent
	$(RM) -r $(AMUTORRENT_DEST_DIR)/etc/default.amutorrent

$(PKG_FINISH)
