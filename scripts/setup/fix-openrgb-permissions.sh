#!/bin/bash
# Fix OpenRGB permissions for current user

ACTUAL_USER="${SUDO_USER:-$USER}"
echo "Fixing OpenRGB permissions for user: $ACTUAL_USER"

# Add ACL permissions for i2c devices
for i in /dev/i2c-*; do
    echo "Setting ACL for $i"
    setfacl -m u:$ACTUAL_USER:rw $i
done

echo "Permissions fixed. Testing OpenRGB..."
su - $ACTUAL_USER -c "openrgb --list-devices | grep -E 'Device|Description' | head -10"