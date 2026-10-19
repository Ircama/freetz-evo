$(call PKG_INIT_BIN, 13.2.4)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=fdd57503b5f591e951ea3dff80ab53a41487c3373dc89370da2e36e7bf752f52
$(PKG)_SITE:=https://github.com/grafana/grafana/archive/refs/tags
### WEBSITE:=https://grafana.com/oss/grafana/
### MANPAGE:=https://grafana.com/docs/grafana/latest/
### CHANGES:=https://github.com/grafana/grafana/releases
### CVSREPO:=https://github.com/grafana/grafana
### SUPPORT:=ircama
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/bin/grafana
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/grafana
$(PKG)_DEPENDS_ON += go-host
$(PKG)_GO_MODCACHE:=$(abspath $($(PKG)_DIR)/.gomodcache)
$(PKG)_GO_CACHE:=$(abspath $($(PKG)_DIR)/.gocache)
$(PKG)_MYSQL_TYPES:=$($(PKG)_GO_MODCACHE)/github.com/grafana/go-mysql-server@v0.20.2-grafana-4/sql/types
$(PKG)_OPENFGA_DIR:=$($(PKG)_GO_MODCACHE)/github.com/openfga/openfga@v1.18.3
$(PKG)_WEB_SOURCE:=grafana-$($(PKG)_VERSION).linux-amd64.tar.gz
$(PKG)_WEB_HASH:=c48765988fd88572607e4ea670251af8a8e64ab3e360d0f3cf67a6f3587b92ab
$(PKG)_WEB_DIR:=$($(PKG)_DIR)/.web
$(PKG)_TARGET_ASSETS:=$($(PKG)_DEST_DIR)/usr/share/grafana/conf/defaults.ini

$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_GO_ARCH FREETZ_TARGET_GO_MIPS FREETZ_TARGET_GO_ARM

ifeq ($(strip $(FREETZ_TARGET_ARCH_MIPS)),y)
$(PKG)_GO_EXTLDFLAGS := -extldflags=-Wl,-T,$(abspath $($(PKG)_MAKE_DIR))/mips-plt.ld
endif

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(DL_DIR)/$(GRAFANA_WEB_SOURCE): | $(DL_DIR)
	$(DL_TOOL) $(DL_DIR) $(GRAFANA_WEB_SOURCE) https://dl.grafana.com/oss/release $(GRAFANA_WEB_HASH)

$(pkg)-download: $(DL_DIR)/$(GRAFANA_WEB_SOURCE)

$(GRAFANA_DIR)/.unpacked: | grafana-precompiled--int
$(GRAFANA_DEST_DIR): | grafana-precompiled--int

$(GRAFANA_WEB_DIR)/.unpacked: $(DL_DIR)/$(GRAFANA_WEB_SOURCE) | grafana-precompiled--int
	mkdir -p $(GRAFANA_WEB_DIR)
	$(TAR) -xzf $< -C $(GRAFANA_WEB_DIR) --strip-components=1 \
		--exclude='*.map' --exclude='*.ts' --exclude='*.tsx' \
		--exclude='*/public/test' --exclude='*/public/sass' \
		grafana-$(GRAFANA_VERSION)/public
	test -s $(GRAFANA_WEB_DIR)/public/views/index.html
	test -d $(GRAFANA_WEB_DIR)/public/build
	touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured $(wildcard $($(PKG)_MAKE_DIR)/module-patches/*.patch) $($(PKG)_MAKE_DIR)/mips-plt.ld
	cd $(GRAFANA_DIR) && \
		export PATH=$(abspath $(TOOLS_DIR))/go-host/bin:$$PATH \
		GOTOOLCHAIN=go1.26.9 GOFLAGS=-modcacherw \
		GOMODCACHE=$(GRAFANA_GO_MODCACHE) GOCACHE=$(GRAFANA_GO_CACHE) \
		GOOS=linux GOARCH=$(FREETZ_TARGET_GO_ARCH) \
		$(if $(FREETZ_TARGET_GO_MIPS),GOMIPS=$(FREETZ_TARGET_GO_MIPS),) \
		$(if $(FREETZ_TARGET_GO_ARM),GOARM=$(FREETZ_TARGET_GO_ARM),) \
		CGO_ENABLED=1 CC="$(TARGET_CC)" \
		CGO_CFLAGS='$(TARGET_CFLAGS)' && \
		if ! test -f pkg/util/sqlite/sqlite_freetz.go; then \
			patch -p1 < $(abspath $(GRAFANA_MAKE_DIR))/module-patches/sqlite-cgo.patch || exit 1; \
		fi && \
		go mod download && \
		chmod u+w $(GRAFANA_OPENFGA_DIR)/pkg/storage/sqlite $(GRAFANA_OPENFGA_DIR)/pkg/storage/sqlite/sqlite.go && \
		if ! test -f $(GRAFANA_OPENFGA_DIR)/pkg/storage/sqlite/sqlite_freetz.go; then \
			patch -d $(GRAFANA_OPENFGA_DIR) -p1 < $(abspath $(GRAFANA_MAKE_DIR))/module-patches/openfga-sqlite-cgo.patch || exit 1; \
		fi && \
		chmod u+w $(GRAFANA_MYSQL_TYPES)/number.go $(GRAFANA_MYSQL_TYPES)/geometry.go && \
		sed -i 's/math.MaxUint64 - uint(-v-1)/math.MaxUint64 - uint64(-v-1)/g' $(GRAFANA_MYSQL_TYPES)/number.go && \
		sed -i 's/srid > math.MaxUint32/uint64(srid) > math.MaxUint32/g' $(GRAFANA_MYSQL_TYPES)/geometry.go && \
		chmod u+w $(GRAFANA_MYSQL_TYPES)/../expression/function/extract.go && \
		if ! grep -q 'int64(dateTime.Hour())' $(GRAFANA_MYSQL_TYPES)/../expression/function/extract.go; then \
			patch -d $(GRAFANA_MYSQL_TYPES)/../.. -p1 < $(abspath $(GRAFANA_MAKE_DIR))/module-patches/mysql-extract-32bit.patch || exit 1; \
		fi && \
		chmod u+w $(GRAFANA_MYSQL_TYPES)/../rowexec/ddl.go $(GRAFANA_MYSQL_TYPES)/../rowexec/proc.go && \
		if ! grep -q 'loopIteration := int64(0)' $(GRAFANA_MYSQL_TYPES)/../rowexec/proc.go; then \
			patch -d $(GRAFANA_MYSQL_TYPES)/../.. -p1 < $(abspath $(GRAFANA_MAKE_DIR))/module-patches/mysql-rowexec-32bit.patch || exit 1; \
		fi && \
		go build -buildvcs=false -trimpath -tags 'oss netgo freetz_sqlite_cgo' \
			-ldflags='-s -w -X main.version=$(GRAFANA_VERSION) $(GRAFANA_GO_EXTLDFLAGS)' \
			-o bin/grafana ./pkg/cmd/grafana

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(GRAFANA_TARGET_ASSETS): $(GRAFANA_WEB_DIR)/.unpacked $(GRAFANA_DIR)/.configured $(GRAFANA_DEST_DIR)
	mkdir -p $(GRAFANA_DEST_DIR)/usr/share/grafana/conf
	cp -a $(GRAFANA_WEB_DIR)/public $(GRAFANA_DEST_DIR)/usr/share/grafana/
	cp $(GRAFANA_DIR)/conf/defaults.ini $@
	cp $(GRAFANA_DIR)/LICENSE $(GRAFANA_DIR)/NOTICE.md $(GRAFANA_DEST_DIR)/usr/share/grafana/
	chmod 755 $(GRAFANA_DEST_DIR)/etc/init.d/rc.grafana $(GRAFANA_DEST_DIR)/usr/lib/cgi-bin/grafana.cgi

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY) $(GRAFANA_TARGET_ASSETS)

$(pkg)-clean:
	$(RM) $(GRAFANA_BINARY) $(GRAFANA_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(GRAFANA_TARGET_BINARY)
	$(RM) -r $(GRAFANA_DEST_DIR)/usr/share/grafana

$(PKG_FINISH)