#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

export PYTHONPATH="/opt/corroventa:/opt/corroventa/vendor${PYTHONPATH:+:$PYTHONPATH}"

# Prefer Supervisor MQTT service; allow options override for advanced setups.
if bashio::services.available "mqtt"; then
  export MQTT_HOST="$(bashio::services mqtt "host")"
  export MQTT_PORT="$(bashio::services mqtt "port")"
  export MQTT_USERNAME="$(bashio::services mqtt "username")"
  export MQTT_PASSWORD="$(bashio::services mqtt "password")"
  bashio::log.info "Using Home Assistant MQTT service at ${MQTT_HOST}:${MQTT_PORT}"
else
  bashio::log.warning "MQTT service not available — set mqtt_* options or install Mosquitto"
fi

if bashio::config.has_value "mqtt_host"; then
  export MQTT_HOST="$(bashio::config "mqtt_host")"
fi
if bashio::config.has_value "mqtt_port"; then
  export MQTT_PORT="$(bashio::config "mqtt_port")"
fi
if bashio::config.has_value "mqtt_username"; then
  export MQTT_USERNAME="$(bashio::config "mqtt_username")"
fi
if bashio::config.has_value "mqtt_password"; then
  export MQTT_PASSWORD="$(bashio::config "mqtt_password")"
fi
if bashio::config.has_value "mqtt_client_id"; then
  export MQTT_CLIENT_ID="$(bashio::config "mqtt_client_id")"
fi

export LOG_LEVEL="$(bashio::config "log_level")"
export RADIO_MODE="$(bashio::config "radio_mode")"
export RADIO_ENABLED="$(bashio::config "radio_enabled")"
export DISCOVERY_PREFIX="$(bashio::config "discovery_prefix")"
export TOPIC_PREFIX="$(bashio::config "topic_prefix")"
export DEVICE_MODEL="$(bashio::config "device_model")"
export TX_REPEATS="$(bashio::config "tx_repeats")"

bashio::log.info "Starting Corroventa MQTT Gateway"
exec python3 -m corroventa_gateway
