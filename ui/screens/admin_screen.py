"""
Admin Dashboard Screen - PyQt5
Inventory reports, system health, expiry management, transactions.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView,
    QMessageBox, QGridLayout, QScrollArea, QFrame
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
import logging
from datetime import datetime
from core.inventory import InventoryManager
from core.expiry import ExpiryManager
from hardware.hardware_manager import get_hardware
from database.db_manager import db

logger = logging.getLogger(__name__)


class AdminScreen(QWidget):
    """Admin dashboard screen."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        self.inventory = InventoryManager(app.app_config)
        self.expiry_mgr = ExpiryManager(app.app_config)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build admin UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel('ADMIN DASHBOARD')
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title, stretch=1)
        
        btn_logout = QPushButton('← Logout')
        btn_logout.setFont(QFont('Arial', 12))
        btn_logout.setFixedWidth(100)
        btn_logout.setStyleSheet("background-color: #CC3333; color: white;")
        btn_logout.clicked.connect(self._on_logout)
        header_layout.addWidget(btn_logout)
        
        layout.addLayout(header_layout)
        
        # Tabbed panel
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont('Arial', 11))
        
        # Create tabs
        self.tabs.addTab(self._build_inventory_panel(), 'Inventory')
        self.tabs.addTab(self._build_transactions_panel(), 'Transactions')
        self.tabs.addTab(self._build_expiry_panel(), 'Expiry Management')
        self.tabs.addTab(self._build_system_panel(), 'System Health')
        
        layout.addWidget(self.tabs)
        
        self.setLayout(layout)
    
    def _build_inventory_panel(self):
        """Build inventory overview panel."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Refresh button
        btn_refresh = QPushButton('🔄 Refresh Data')
        btn_refresh.setFont(QFont('Arial', 11))
        btn_refresh.setFixedHeight(40)
        btn_refresh.setStyleSheet("background-color: #33CC33; color: white;")
        btn_refresh.clicked.connect(self._refresh_inventory)
        layout.addWidget(btn_refresh)
        
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.inv_content = QWidget()
        self.inv_layout = QVBoxLayout()
        self.inv_layout.setSpacing(10)
        self.inv_content.setLayout(self.inv_layout)
        
        scroll.setWidget(self.inv_content)
        layout.addWidget(scroll)
        
        panel.setLayout(layout)
        
        # Load initial data
        self._refresh_inventory()
        
        return panel
    
    def _refresh_inventory(self):
        """Refresh inventory display."""
        # Clear existing widgets
        while self.inv_layout.count():
            child = self.inv_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Summary
        stock_summary = self.inventory.get_stock_summary()
        total_stock = self.inventory.get_total_stock()
        total_capacity = self.app.app_config.get('capacity', {}).get('total', 100000)
        
        # Total stock widget
        total_widget = QFrame()
        total_widget.setFrameShape(QFrame.Box)
        total_widget.setStyleSheet("background-color: #E8F5E9; border: 2px solid #4CAF50; border-radius: 5px;")
        total_layout = QVBoxLayout()
        
        total_title = QLabel('📊 TOTAL STOCK')
        total_title.setFont(QFont('Arial', 14, QFont.Bold))
        total_layout.addWidget(total_title)
        
        total_value = QLabel(f'{total_stock:.2f} kg / {total_capacity:.2f} kg')
        total_value.setFont(QFont('Arial', 16))
        total_layout.addWidget(total_value)
        
        utilization = (total_stock / total_capacity * 100) if total_capacity > 0 else 0
        util_label = QLabel(f'Utilization: {utilization:.1f}%')
        util_label.setFont(QFont('Arial', 12))
        total_layout.addWidget(util_label)
        
        total_widget.setLayout(total_layout)
        total_widget.setFixedHeight(120)
        self.inv_layout.addWidget(total_widget)
        
        # Per-crop breakdown
        for crop_data in stock_summary:
            crop_widget = QFrame()
            crop_widget.setFrameShape(QFrame.Box)
            crop_widget.setStyleSheet("background-color: #F5F5F5; border: 1px solid #CCCCCC; border-radius: 5px;")
            crop_layout = QVBoxLayout()
            
            # Crop name
            crop_name = QLabel(f'🌾 {crop_data["crop_type"].upper()}')
            crop_font = QFont('Arial', 13, QFont.Bold)
            crop_name.setFont(crop_font)
            crop_layout.addWidget(crop_name)
            
            # Stock info
            stock_info = QLabel(
                f'Stock: {crop_data["current_stock_kg"]:.2f} kg / {crop_data["allocated_capacity_kg"]:.2f} kg'
            )
            stock_info.setFont(QFont('Arial', 11))
            crop_layout.addWidget(stock_info)
            
            # Available space
            available_info = QLabel(f'Available: {crop_data["available_kg"]:.2f} kg')
            available_info.setFont(QFont('Arial', 11))
            crop_layout.addWidget(available_info)
            
            # Utilization percentage
            util_percent = crop_data['utilization_percent']
            util_label = QLabel(f'Utilization: {util_percent:.1f}%')
            util_label.setFont(QFont('Arial', 11))
            
            # Color code based on utilization
            if util_percent > 90:
                util_label.setStyleSheet("color: red; font-weight: bold;")
            elif util_percent > 70:
                util_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                util_label.setStyleSheet("color: green;")
            
            crop_layout.addWidget(util_label)
            
            crop_widget.setLayout(crop_layout)
            crop_widget.setFixedHeight(130)
            self.inv_layout.addWidget(crop_widget)
        
        self.inv_layout.addStretch()
    
    def _build_transactions_panel(self):
        """Build transactions panel."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Filter buttons
        filter_layout = QHBoxLayout()
        
        filters = [
            ('All', None),
            ('Storage', 'storage'),
            ('Selling', 'selling'),
            ('Buying', 'buying')
        ]
        
        self.current_txn_filter = None
        
        for text, filter_type in filters:
            btn = QPushButton(text)
            btn.setFont(QFont('Arial', 10))
            btn.setFixedHeight(35)
            btn.clicked.connect(lambda checked, ft=filter_type: self._filter_transactions(ft))
            filter_layout.addWidget(btn)
        
        layout.addLayout(filter_layout)
        
        # Transactions table
        self.txn_table = QTableWidget()
        self.txn_table.setColumnCount(7)
        self.txn_table.setHorizontalHeaderLabels([
            'Transaction Code', 'Type', 'Farmer', 'Crop', 'Weight (kg)', 'Amount (₹)', 'Date'
        ])
        
        # Set column widths
        header = self.txn_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.txn_table.setAlternatingRowColors(True)
        self.txn_table.setFont(QFont('Arial', 10))
        
        layout.addWidget(self.txn_table)
        
        # Export button
        btn_export = QPushButton('📥 Export to Excel')
        btn_export.setFont(QFont('Arial', 11))
        btn_export.setFixedHeight(40)
        btn_export.setStyleSheet("background-color: #2196F3; color: white;")
        btn_export.clicked.connect(self._export_transactions)
        layout.addWidget(btn_export)
        
        panel.setLayout(layout)
        
        # Load initial data
        self._load_transactions()
        
        return panel
    
    def _filter_transactions(self, txn_filter):
        """Filter transactions by type."""
        self.current_txn_filter = txn_filter
        self._load_transactions()
    
    def _load_transactions(self):
        """Load transaction list."""
        query = """
        SELECT t.*, f.name as farmer_name
        FROM transactions t
        JOIN farmers f ON t.farmer_id = f.id
        """
        
        params = []
        
        if self.current_txn_filter:
            query += " WHERE t.txn_type = ?"
            params.append(self.current_txn_filter)
        
        query += " ORDER BY t.txn_date DESC LIMIT 100"
        
        transactions = db.fetchall(query, tuple(params))
        
        self.txn_table.setRowCount(len(transactions))
        
        for row, txn in enumerate(transactions):
            self.txn_table.setItem(row, 0, QTableWidgetItem(txn['txn_code']))
            self.txn_table.setItem(row, 1, QTableWidgetItem(txn['txn_type'].upper()))
            self.txn_table.setItem(row, 2, QTableWidgetItem(txn['farmer_name']))
            self.txn_table.setItem(row, 3, QTableWidgetItem(txn['crop_type'].upper()))
            self.txn_table.setItem(row, 4, QTableWidgetItem(f"{txn['weight_kg']:.2f}"))
            self.txn_table.setItem(row, 5, QTableWidgetItem(f"₹{txn['amount']:.2f}"))
            
            txn_date = datetime.fromisoformat(txn['txn_date']).strftime('%d/%m/%Y %H:%M')
            self.txn_table.setItem(row, 6, QTableWidgetItem(txn_date))
    
    def _export_transactions(self):
        """Export transactions to Excel."""
        QMessageBox.information(self, 'Export', 'Export functionality will be implemented using openpyxl')
        # TODO: Implement Excel export
    
    def _build_expiry_panel(self):
        """Build expiry management panel."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        btn_check = QPushButton('🔍 Run Expiry Check')
        btn_check.setFont(QFont('Arial', 11))
        btn_check.setFixedHeight(40)
        btn_check.setStyleSheet("background-color: #FF9800; color: white;")
        btn_check.clicked.connect(self._run_expiry_check)
        action_layout.addWidget(btn_check)
        
        btn_warnings = QPushButton('📱 Send Warnings')
        btn_warnings.setFont(QFont('Arial', 11))
        btn_warnings.setFixedHeight(40)
        btn_warnings.setStyleSheet("background-color: #2196F3; color: white;")
        btn_warnings.clicked.connect(self._send_expiry_warnings)
        action_layout.addWidget(btn_warnings)
        
        layout.addLayout(action_layout)
        
        # Expiring batches table
        self.exp_table = QTableWidget()
        self.exp_table.setColumnCount(6)
        self.exp_table.setHorizontalHeaderLabels([
            'Batch Code', 'Farmer', 'Crop', 'Weight (kg)', 'Expiry Date', 'Days Left'
        ])
        
        header = self.exp_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        self.exp_table.setAlternatingRowColors(True)
        self.exp_table.setFont(QFont('Arial', 10))
        
        layout.addWidget(self.exp_table)
        
        # Confiscated batches section
        confiscated_label = QLabel('📦 Confiscated Batches')
        confiscated_label.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addWidget(confiscated_label)
        
        self.conf_table = QTableWidget()
        self.conf_table.setColumnCount(5)
        self.conf_table.setHorizontalHeaderLabels([
            'Batch Code', 'Farmer', 'Crop', 'Weight (kg)', 'Confiscation Date'
        ])
        
        conf_header = self.conf_table.horizontalHeader()
        conf_header.setSectionResizeMode(QHeaderView.Stretch)
        
        self.conf_table.setAlternatingRowColors(True)
        self.conf_table.setFont(QFont('Arial', 10))
        self.conf_table.setMaximumHeight(200)
        
        layout.addWidget(self.conf_table)
        
        panel.setLayout(layout)
        
        # Load initial data
        self._load_expiring_batches()
        
        return panel
    
    def _run_expiry_check(self):
        """Run expiry check and confiscation."""
        result = self.expiry_mgr.daily_expiry_check(self.app.current_language)
        
        QMessageBox.information(
            self, 
            'Expiry Check Complete',
            f"Expiry Check Results:\n\n"
            f"Warnings Sent: {result['warnings_sent']}\n"
            f"Batches Confiscated: {result['confiscated']}\n\n"
            f"Timestamp: {result['timestamp']}"
        )
        
        self._load_expiring_batches()
    
    def _send_expiry_warnings(self):
        """Send expiry warnings."""
        count = self.expiry_mgr.send_expiry_warnings(self.app.current_language)
        QMessageBox.information(
            self, 
            'Warnings Sent', 
            f'Sent {count} expiry warnings via WhatsApp'
        )
    
    def _load_expiring_batches(self):
        """Load expiring batches."""
        # Expiring batches (next 30 days)
        expiring = self.expiry_mgr.check_expiring_batches(warning_days=30)
        
        self.exp_table.setRowCount(len(expiring))
        
        for row, batch in enumerate(expiring):
            self.exp_table.setItem(row, 0, QTableWidgetItem(batch['batch_code']))
            self.exp_table.setItem(row, 1, QTableWidgetItem(batch['farmer_name']))
            self.exp_table.setItem(row, 2, QTableWidgetItem(batch['crop_type'].upper()))
            self.exp_table.setItem(row, 3, QTableWidgetItem(f"{batch['weight_kg']:.2f}"))
            
            expiry_date = datetime.fromisoformat(batch['expiry_date']).date()
            self.exp_table.setItem(row, 4, QTableWidgetItem(expiry_date.strftime('%d/%m/%Y')))
            
            days_left = (expiry_date - datetime.now().date()).days
            days_item = QTableWidgetItem(str(days_left))
            
            # Color code based on days left
            if days_left < 7:
                days_item.setBackground(QColor(255, 200, 200))  # Red
            elif days_left < 14:
                days_item.setBackground(QColor(255, 230, 150))  # Orange
            
            self.exp_table.setItem(row, 5, days_item)
        
        # Confiscated batches
        confiscated = self.expiry_mgr.get_confiscated_inventory()
        
        self.conf_table.setRowCount(len(confiscated))
        
        for row, batch in enumerate(confiscated):
            self.conf_table.setItem(row, 0, QTableWidgetItem(batch['batch_code']))
            self.conf_table.setItem(row, 1, QTableWidgetItem(batch['farmer_name']))
            self.conf_table.setItem(row, 2, QTableWidgetItem(batch['crop_type'].upper()))
            self.conf_table.setItem(row, 3, QTableWidgetItem(f"{batch['weight_kg']:.2f}"))
            
            conf_date = batch['confiscation_date']
            self.conf_table.setItem(row, 4, QTableWidgetItem(conf_date if conf_date else 'N/A'))
    
    def _build_system_panel(self):
        """Build system health panel."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # System info grid
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Box)
        info_frame.setStyleSheet("background-color: #F5F5F5; border: 1px solid #CCCCCC;")
        info_layout = QGridLayout()
        info_layout.setSpacing(10)
        
        row = 0
        
        # Godown ID
        info_layout.addWidget(QLabel('Godown ID:'), row, 0)
        godown_id_label = QLabel(self.app.app_config.get('godown_id', 'N/A'))
        godown_id_label.setFont(QFont('Arial', 11, QFont.Bold))
        info_layout.addWidget(godown_id_label, row, 1)
        row += 1
        
        # Godown Name
        info_layout.addWidget(QLabel('Godown Name:'), row, 0)
        info_layout.addWidget(QLabel(self.app.app_config.get('godown_name', 'N/A')), row, 1)
        row += 1
        
        # Simulation Mode
        info_layout.addWidget(QLabel('Simulation Mode:'), row, 0)
        sim_mode = 'YES' if self.app.app_config.get('simulation_mode') else 'NO'
        sim_label = QLabel(sim_mode)
        sim_label.setFont(QFont('Arial', 11, QFont.Bold))
        sim_label.setStyleSheet("color: red;" if sim_mode == 'YES' else "color: green;")
        info_layout.addWidget(sim_label, row, 1)
        row += 1
        
        # Total Capacity
        info_layout.addWidget(QLabel('Total Capacity:'), row, 0)
        capacity = self.app.app_config.get('capacity', {}).get('total', 0)
        info_layout.addWidget(QLabel(f"{capacity:.2f} kg"), row, 1)
        row += 1
        
        # Current Stock
        info_layout.addWidget(QLabel('Current Stock:'), row, 0)
        current_stock = self.inventory.get_total_stock()
        stock_label = QLabel(f"{current_stock:.2f} kg")
        stock_label.setFont(QFont('Arial', 11, QFont.Bold))
        stock_label.setStyleSheet("color: green;")
        info_layout.addWidget(stock_label, row, 1)
        row += 1
        
        info_frame.setLayout(info_layout)
        layout.addWidget(info_frame)
        
        # Hardware health
        health_label = QLabel('🔧 Hardware Status')
        health_label.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addWidget(health_label)
        
        hw = get_hardware()
        health = hw.get_health_status()
        
        health_frame = QFrame()
        health_frame.setFrameShape(QFrame.Box)
        health_frame.setStyleSheet("background-color: #F5F5F5; border: 1px solid #CCCCCC;")
        health_layout = QGridLayout()
        
        row = 0
        for component, status in health.items():
            health_layout.addWidget(QLabel(f'{component.upper()}:'), row, 0)
            
            status_label = QLabel(status.upper())
            status_label.setFont(QFont('Arial', 11, QFont.Bold))
            
            if status == 'ok':
                status_label.setStyleSheet("color: green;")
            else:
                status_label.setStyleSheet("color: red;")
            
            health_layout.addWidget(status_label, row, 1)
            row += 1
        
        health_frame.setLayout(health_layout)
        layout.addWidget(health_frame)
        
        layout.addStretch()
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        btn_vacuum = QPushButton('🗄️ Vacuum Database')
        btn_vacuum.setFont(QFont('Arial', 11))
        btn_vacuum.setFixedHeight(40)
        btn_vacuum.setStyleSheet("background-color: #FF9800; color: white;")
        btn_vacuum.clicked.connect(self._vacuum_db)
        action_layout.addWidget(btn_vacuum)
        
        btn_backup = QPushButton('💾 Backup Now')
        btn_backup.setFont(QFont('Arial', 11))
        btn_backup.setFixedHeight(40)
        btn_backup.setStyleSheet("background-color: #2196F3; color: white;")
        btn_backup.clicked.connect(self._backup_db)
        action_layout.addWidget(btn_backup)
        
        layout.addLayout(action_layout)
        
        panel.setLayout(layout)
        
        return panel
    
    def _vacuum_db(self):
        """Vacuum database."""
        try:
            db.vacuum()
            QMessageBox.information(self, 'Database', 'Database vacuumed successfully!')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Vacuum failed: {str(e)}')
    
    def _backup_db(self):
        """Backup database."""
        QMessageBox.information(self, 'Backup', 'Manual backup functionality will run backup script')
        # TODO: Implement backup script call
    
    def _on_logout(self):
        """Logout and return to startup."""
        self.app.show_screen('startup')