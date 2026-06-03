#!/bin/bash
# Start all Sanjeevani services

echo "Starting Sanjeevani Shelf services..."

sudo systemctl start sanjeevani-shelf
sudo systemctl start sanjeevani-whatsapp

echo ""
echo "Service status:"
echo "==============="
sudo systemctl status sanjeevani-shelf --no-pager -l
echo ""
sudo systemctl status sanjeevani-whatsapp --no-pager -l
echo ""

echo "To view logs:"
echo "  journalctl -u sanjeevani-shelf -f"
echo "  journalctl -u sanjeevani-whatsapp -f"