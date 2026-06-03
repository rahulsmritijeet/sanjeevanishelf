#!/bin/bash
# Manual backup script

BACKUP_DIR="/media/usb/backups"
PROJECT_DIR="/opt/sanjeevani_shelf"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Sanjeevani Shelf Backup Script"
echo "==============================="

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Backup database
echo "Backing up database..."
cp "$PROJECT_DIR/data/godown.db" "$BACKUP_DIR/godown_$DATE.db"

# Backup configuration
echo "Backing up configuration..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C "$PROJECT_DIR" config/

# Backup logs (last 7 days)
echo "Backing up recent logs..."
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" -C "$PROJECT_DIR" logs/ --exclude='*.gz'

# Clean old backups (keep 30 days)
echo "Cleaning old backups..."
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo ""
echo "Backup complete!"
echo "Location: $BACKUP_DIR"
echo "Files:"
ls -lh "$BACKUP_DIR" | tail -3
echo ""