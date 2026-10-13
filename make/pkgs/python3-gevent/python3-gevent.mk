$(call PKG_INIT_BIN, 26.9.0)
$(PKG)_SOURCE:=gevent-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=gevent-26.9.0.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/g/gevent
$(PKG)_HASH:=4dd4703d71737a456c1c9df5cd43a82934e5b10c87549caa02495f487d1ef0b1
### WEBSITE:=https://pypi.org/project/gevent/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += libev
$(PKG)_DEPENDS_ON += libcares
$(PKG)_DEPENDS_ON += python3-greenlet
$(PKG)_DEPENDS_ON += python3-cffi
$(PKG)_DEPENDS_ON += python3-zope-event
$(PKG)_DEPENDS_ON += python3-zope-interface

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/gevent/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
# gevent embeds its own copy of libev by default, whose configure checks the
# compiler by running a compiled program - impossible when cross compiling. Use
# the libev of this tree instead (LIBEV_CFLAGS/LIBEV_LIBS below).
	$(SED) -i -e 's|^LIBEV_EMBED = should_embed.*|LIBEV_EMBED = False|' $(PYTHON3_GEVENT_DIR)/_setuplibev.py
# Same for the bundled c-ares, whose configure also runs compiled programs.
	$(SED) -i -e 's|^CARES_EMBED = should_embed.*|CARES_EMBED = False|' $(PYTHON3_GEVENT_DIR)/_setupares.py
# get_include_dirs() prepends the include directory of the interpreter that runs
# the build, which is the host Python: its 64 bit headers fail the LONG_BIT check
# of the 32 bit target. Point all of them at the target include directory that
# freetz exports in PYTHON3_INCDIR.
	$(SED) -i \
		-e "s|^    dist_inc_dir = .*|    dist_inc_dir = os.environ.get('PYTHON3_INCDIR', '')|" \
		-e "s|^    sys_inc_dir = .*|    sys_inc_dir = os.environ.get('PYTHON3_INCDIR', '')|" \
		-e "s|^    venv_include_dir = os.path.abspath(venv_include_dir)|    venv_include_dir = os.environ.get('PYTHON3_INCDIR', '')|" \
		$(PYTHON3_GEVENT_DIR)/_setuputils.py
	$(call Build/PyMod3/PKG, PYTHON3_GEVENT, , LIBEV_CFLAGS="-I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include" LIBEV_LIBS="-L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -lev")

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_GEVENT_DIR)/.configured
	$(RM) -r $(PYTHON3_GEVENT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_GEVENT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/gevent \
		$(PYTHON3_GEVENT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/gevent-*.dist-info

$(PKG_FINISH)
