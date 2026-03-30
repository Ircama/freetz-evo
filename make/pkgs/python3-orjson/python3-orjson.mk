$(call PKG_INIT_BIN, 3.10.7)
### WEBSITE:=https://github.com/ijl/orjson
### NOTE:=This package installs a pure-Python compatibility shim.

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/orjson.py

$(PKG_UNPACKED)

$($(PKG)_TARGET_BINARY):
	@mkdir -p $(@D)
	cp ./make/pkgs/python3-orjson/files/orjson.py $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) -r $(PYTHON3_ORJSON_DIR)/build

$(pkg)-uninstall:
	$(RM) -f \
		$(PYTHON3_ORJSON_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/orjson.py

$(PKG_FINISH)