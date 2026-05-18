$(call PKG_INIT_LIB, 0.9.26)
$(PKG)_SOURCE:=caps_$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=e7496c5bce05abebe3dcb635926153bbb58a9337a6e423f048d3b61d8a4f98c9
$(PKG)_SITE:=https://quitte.de/dsp
### WEBSITE:=https://quitte.de/dsp/caps.html
### MANPAGE:=https://quitte.de/dsp/caps.html
### CHANGES:=https://quitte.de/dsp/caps.html
### PKGSITE:=https://github.com/Ircama/freetz-evo/tree/master/make/libs/caps/

$(PKG)_BINARY:=$($(PKG)_DIR)/caps.so
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ladspa/caps.so
$(PKG)_STAGING_RDF:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/ladspa/rdf/caps.rdf
$(PKG)_TARGET_BINARY:=$(TARGET_DIR)/usr/lib/ladspa/caps.so
$(PKG)_TARGET_RDF:=$(TARGET_DIR)/usr/share/ladspa/rdf/caps.rdf

$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

CAPS_MAKE_ENV := \
	CC="$(TARGET_CXX)" \
	STRIP="$(TARGET_STRIP)" \
	PREFIX=/usr \
	DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
	ARCH= \
	_CFLAGS= \
	_LDFLAGS="-shared -lm"

CAPS_MAKE_OPTS := \
	OPTS="$(TARGET_CFLAGS) -O3 -ffast-math -funroll-loops -Wall -fPIC -DPIC"

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(CAPS_DIR) \
		$(CAPS_MAKE_ENV) \
		$(CAPS_MAKE_OPTS) \
		all

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(CAPS_DIR) \
		$(CAPS_MAKE_ENV) \
		$(CAPS_MAKE_OPTS) \
		install

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_FILE) $(CAPS_STAGING_BINARY) $(TARGET_DIR)/usr/lib/ladspa/
	$(TARGET_STRIP) $(CAPS_TARGET_BINARY) 2>/dev/null || true
	$(INSTALL_FILE) $(CAPS_STAGING_RDF) $(TARGET_DIR)/usr/share/ladspa/rdf/

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(CAPS_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/ladspa/caps.so \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/ladspa/rdf/caps.rdf

$(pkg)-uninstall:
	$(RM) -f \
		$(TARGET_DIR)/usr/lib/ladspa/caps.so \
		$(TARGET_DIR)/usr/share/ladspa/rdf/caps.rdf

$(PKG_FINISH)
