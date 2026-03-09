#!/bin/bash
# Install OpenRGB server, RGB daemon, and RGB Control Streamlit app as systemd services
# Run with: sudo bash install-service.sh

set -e

# Install OpenRGB server service
cp openrgb-server.service /etc/systemd/system/openrgb-server.service
echo "Installed openrgb-server.service"

# Install RGB daemon service
cp rgb-daemon.service /etc/systemd/system/rgb-daemon.service
echo "Installed rgb-daemon.service"

# Install RGB Control Streamlit service
cp rgb-control.service /etc/systemd/system/rgb-control.service
echo "Installed rgb-control.service"

systemctl daemon-reload
systemctl enable --now openrgb-server
systemctl enable --now rgb-daemon
systemctl enable --now rgb-control

echo ""
echo "Services installed and started."
echo ""
echo "OpenRGB server:"
systemctl status openrgb-server --no-pager
echo ""
echo "RGB daemon:"
systemctl status rgb-daemon --no-pager
echo ""
echo "RGB Control (Streamlit on port 8510):"
systemctl status rgb-control --no-pager
