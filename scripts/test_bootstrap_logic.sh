#!/bin/bash
# Test script to verify the logic of config.env detection in bootstrap.sh

# Mock environments
TEST_DIR="test_bootstrap_env"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Mock config.env
echo "TEST_CONFIG=true" > config.env

# Run the logic snippet (extracted from bootstrap.sh)
CURRENT_CONFIG="$PWD/config.env"
# Mock installation dir
DIR="$PWD/install_dir"
mkdir -p "$DIR"
CONFIG_FILE="$DIR/config.env"
USER=$(whoami)

echo "--- Test 1: config.env exists in current dir ---"
if [ -f "$CURRENT_CONFIG" ]; then
  echo "Found config.env in current directory, installing..."
  cp "$CURRENT_CONFIG" "$CONFIG_FILE"
  # Mock chmod/chown to avoid errors if not root
  # chmod 600 "$CONFIG_FILE"
  # chown "$USER:$USER" "$CONFIG_FILE"
  echo "Success: Copied to $CONFIG_FILE"
elif [ -f "$CONFIG_FILE" ]; then
  echo "Found existing configuration at $CONFIG_FILE, preserving..."
else
  echo "ERROR: No config.env found!"
  exit 1
fi

if [ -f "$CONFIG_FILE" ]; then
    echo "PASS: Config file detected and copied."
else
    echo "FAIL: Config file not found in install dir."
fi

# Cleanup
rm -rf "$TEST_DIR"
