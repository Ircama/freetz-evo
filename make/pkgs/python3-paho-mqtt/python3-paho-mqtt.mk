$(call PKG_INIT_BIN, 2.1.0)
# The sdist of PyPI is called paho_mqtt-<version>.tar.gz, the module it installs
# is `paho`.
$(PKG)_SOURCE:=paho-mqtt-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=paho_mqtt-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/paho-mqtt
$(PKG)_HASH:=12d6e7511d4137555a3f6ea167ae846af2c7357b10bc6fa4f7c3968fc1723834
### WEBSITE:=https://eclipse.dev/paho/
### CHANGES:=https://github.com/eclipse-paho/paho.mqtt.python/releases
### CVSREPO:=https://github.com/eclipse-paho/paho.mqtt.python
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/paho/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PAHO_MQTT, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PAHO_MQTT_DIR)/.configured
	$(RM) -r $(PYTHON3_PAHO_MQTT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PAHO_MQTT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/paho \
		$(PYTHON3_PAHO_MQTT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/paho_mqtt-*.dist-info

$(PKG_FINISH)
