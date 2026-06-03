#!/bin/bash
# Sanjeevani Shelf v1.1 Installation Script
# Run as: sudo ./install.sh

set -e

echo "=========================================="
echo "Sanjeevani Shelf v1.1 Installation"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

# Update system
echo "Updating system..."
apt-get update
apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
apt-get install -y     python3     python3-pip     python3-venv     git     sqlite3     bluez     bluetooth     libbluetooth-dev     libsdl2-dev     libsdl2-image-dev     libsdl2-mixer-dev     libsdl2-ttf-dev     pkg-config     libgl1-mesa-dev     libgles2-mesa-dev     gstreamer1.0-plugins-base     gstreamer1.0-plugins-good

# Setup project directory
PROJECT_DIR="/opt/sanjeevani_shelf"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Creating project directory..."
    mkdir -p "$PROJECT_DIR"
    cp -r . "$PROJECT_DIR/"
else
    echo "Project directory exists, updating..."
    cp -r . "$PROJECT_DIR/"
fi

cd "$PROJECT_DIR"

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate venv and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p data logs reports

# Initialize database
echo "Initializing database..."
python3 -c "from database.migrations import apply_migrations; apply_migrations()"

# Setup Bluetooth (if not in simulation)
echo "Setting up Bluetooth..."
systemctl enable bluetooth
systemctl start bluetooth

# Create systemd service for main app
echo "Creating systemd service..."
cat > /etc/systemd/system/sanjeevani-shelf.service <<EOF
[Unit]
Description=Sanjeevani Shelf Godown Management System
After=network.target bluetooth.target

[Service]
Type=simple
User=pi
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/ui/app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for WhatsApp queue
cat > /etc/systemd/system/sanjeevani-whatsapp.service <<EOF
[Unit]
Description=Sanjeevani Shelf WhatsApp Queue Processor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python -c "from comms.whatsapp_queue import *; import time; wq = WhatsAppQueue({}); wq.start(); time.sleep(999999)"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create daily expiry check cron job
echo "Setting up cron jobs..."
cat > /etc/cron.daily/sanjeevani-expiry <<EOF
#!/bin/bash
cd $PROJECT_DIR
source venv/bin/activate
python3 -c "from core.expiry import ExpiryManager; import yaml; config = yaml.safe_load(open('config/settings.yaml')); mgr = ExpiryManager(config); mgr.daily_expiry_check('en')"
EOF
chmod +x /etc/cron.daily/sanjeevani-expiry

# Create backup script
echo "Setting up backup..."
cat > /usr/local/bin/sanjeevani-backup <<EOF
#!/bin/bash
BACKUP_DIR="/media/usb/backups"
DATE=\$(date +%Y%m%d_%H%M%S)

if [ -d "\$BACKUP_DIR" ]; then
    mkdir -p "\$BACKUP_DIR"
    cp $PROJECT_DIR/data/godown.db "\$BACKUP_DIR/godown_\$DATE.db"
    
    # Keep only last 30 days
    find "\$BACKUP_DIR" -name "godown_*.db" -mtime +30 -delete
    
    echo "Backup complete: godown_\$DATE.db"
else
    echo "Backup directory not found: \$BACKUP_DIR"
fi
EOF
chmod +x /usr/local/bin/sanjeevani-backup

# Add backup to cron
echo "0 2 * * * root /usr/local/bin/sanjeevani-backup" >> /etc/crontab

# Set permissions
echo "Setting permissions..."
chown -R pi:pi "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"

# Reload systemd
systemctl daemon-reload

# Enable services (but don't start yet)
systemctl enable sanjeevani-shelf.service
systemctl enable sanjeevani-whatsapp.service

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure Bluetooth pairing (see README)"
echo "2. Edit config/settings.yaml as needed"
echo "3. Start services:"
echo "   sudo systemctl start sanjeevani-shelf"
echo "   sudo systemctl start sanjeevani-whatsapp"
echo "4. Check status:"
echo "   sudo systemctl status sanjeevani-shelf"
echo ""
echo "Logs: $PROJECT_DIR/logs/"
echo "Data: $PROJECT_DIR/data/"
echo ""