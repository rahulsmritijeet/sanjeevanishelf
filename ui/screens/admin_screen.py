"""
Admin Dashboard Screen
Inventory reports, system health, expiry management.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
import logging
from datetime import datetime
from core.inventory import InventoryManager
from core.expiry import ExpiryManager
from database.db_manager import db

logger = logging.getLogger(__name__)


class AdminScreen(Screen):
    """Admin dashboard screen."""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'admin'
        
        self.inventory = InventoryManager(app_instance.config)
        self.expiry_mgr = ExpiryManager(app_instance.config)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build admin UI."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = BoxLayout(size_hint_y=0.1, spacing=10)
        
        header.add_widget(Label(
            text='[b]ADMIN DASHBOARD[/b]',
            markup=True,
            font_size='28sp'
        ))
        
        btn_back = Button(
            text='← Logout',
            font_size='20sp',
            size_hint_x=0.2,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        btn_back.bind(on_press=self._on_logout)
        header.add_widget(btn_back)
        
        layout.add_widget(header)
        
        # Tabbed panel
        self.tabs = TabbedPanel(do_default_tab=False)
        
        # Inventory tab
        inv_tab = TabbedPanelItem(text='Inventory')
        inv_tab.add_widget(self._build_inventory_panel())
        self.tabs.add_widget(inv_tab)
        
        # Transactions tab
        txn_tab = TabbedPanelItem(text='Transactions')
        txn_tab.add_widget(self._build_transactions_panel())
        self.tabs.add_widget(txn_tab)
        
        # Expiry tab
        exp_tab = TabbedPanelItem(text='Expiry')
        exp_tab.add_widget(self._build_expiry_panel())
        self.tabs.add_widget(exp_tab)
        
        # System tab
        sys_tab = TabbedPanelItem(text='System')
        sys_tab.add_widget(self._build_system_panel())
        self.tabs.add_widget(sys_tab)
        
        layout.add_widget(self.tabs)
        
        self.add_widget(layout)
    
    def _build_inventory_panel(self):
        """Build inventory overview panel."""
        panel = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Refresh button
        btn_refresh = Button(
            text='Refresh Data',
            font_size='18sp',
            size_hint_y=0.1,
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_refresh.bind(on_press=self._refresh_inventory)
        panel.add_widget(btn_refresh)
        
        # Scrollable content
        scroll = ScrollView(size_hint=(1, 0.9))
        
        self.inv_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.inv_content.bind(minimum_height=self.inv_content.setter('height'))
        
        scroll.add_widget(self.inv_content)
        panel.add_widget(scroll)
        
        # Load initial data
        self._refresh_inventory()
        
        return panel
    
    def _refresh_inventory(self, *args):
        """Refresh inventory display."""
        self.inv_content.clear_widgets()
        
        # Summary
        stock_summary = self.inventory.get_stock_summary()
        total_stock = self.inventory.get_total_stock()
        
        self.inv_content.add_widget(Label(
            text=f"[b]Total Stock: {total_stock:.2f} kg[/b]",
            markup=True,
            font_size='22sp',
            size_hint_y=None,
            height=40
        ))
        
        # Per-crop breakdown
        for crop_data in stock_summary:
            crop_widget = BoxLayout(orientation='vertical', size_hint_y=None, height=100, padding=5)
            crop_widget.canvas.before.clear()
            
            from kivy.graphics import Color, Rectangle
            with crop_widget.canvas.before:
                Color(0.9, 0.9, 0.9, 1)
                crop_widget.rect = Rectangle(size=crop_widget.size, pos=crop_widget.pos)
            
            crop_widget.bind(size=lambda obj, val: setattr(obj.rect, 'size', val))
            crop_widget.bind(pos=lambda obj, val: setattr(obj.rect, 'pos', val))
            
            crop_widget.add_widget(Label(
                text=f"[b]{crop_data['crop_type'].upper()}[/b]",
                markup=True,
                font_size='20sp',
                size_hint_y=0.3
            ))
            
            crop_widget.add_widget(Label(
                text=f"Stock: {crop_data['current_stock_kg']:.2f} / {crop_data['allocated_capacity_kg']:.2f} kg",
                font_size='16sp',
                size_hint_y=0.35
            ))
            
            crop_widget.add_widget(Label(
                text=f"Utilization: {crop_data['utilization_percent']:.1f}%",
                font_size='16sp',
                size_hint_y=0.35
            ))
            
            self.inv_content.add_widget(crop_widget)
    
    def _build_transactions_panel(self):
        """Build transactions panel."""
        panel = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Filter buttons
        filter_box = BoxLayout(size_hint_y=0.1, spacing=5)
        
        for txn_type in ['All', 'Storage', 'Selling', 'Buying']:
            btn = Button(text=txn_type, font_size='16sp')
            btn.txn_filter = txn_type.lower() if txn_type != 'All' else None
            btn.bind(on_press=self._filter_transactions)
            filter_box.add_widget(btn)
        
        panel.add_widget(filter_box)
        
        # Scrollable list
        scroll = ScrollView(size_hint=(1, 0.9))
        
        self.txn_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.txn_content.bind(minimum_height=self.txn_content.setter('height'))
        
        scroll.add_widget(self.txn_content)
        panel.add_widget(scroll)
        
        self._load_transactions()
        
        return panel
    
    def _filter_transactions(self, button):
        """Filter transactions by type."""
        self.current_txn_filter = button.txn_filter
        self._load_transactions()
    
    def _load_transactions(self, txn_filter=None):
        """Load transaction list."""
        self.txn_content.clear_widgets()
        
        query = """
        SELECT t.*, f.name as farmer_name
        FROM transactions t
        JOIN farmers f ON t.farmer_id = f.id
        """
        
        if txn_filter:
            query += f" WHERE t.txn_type = '{txn_filter}'"
        
        query += " ORDER BY t.txn_date DESC LIMIT 50"
        
        transactions = db.fetchall(query)
        
        for txn in transactions:
            txn_widget = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, padding=5, spacing=5)
            
            from kivy.graphics import Color, Rectangle
            with txn_widget.canvas.before:
                Color(0.95, 0.95, 0.95, 1)
                txn_widget.rect = Rectangle(size=txn_widget.size, pos=txn_widget.pos)
            
            txn_widget.bind(size=lambda obj, val: setattr(obj.rect, 'size', val))
            txn_widget.bind(pos=lambda obj, val: setattr(obj.rect, 'pos', val))
            
            txn_widget.add_widget(Label(
                text=txn['txn_code'],
                font_size='14sp',
                size_hint_x=0.25
            ))
            
            txn_widget.add_widget(Label(
                text=txn['farmer_name'],
                font_size='14sp',
                size_hint_x=0.25
            ))
            
            txn_widget.add_widget(Label(
                text=f"{txn['crop_type']} - {txn['weight_kg']:.2f}kg",
                font_size='14sp',
                size_hint_x=0.25
            ))
            
            txn_widget.add_widget(Label(
                text=f"₹{txn['amount']:.2f}",
                font_size='14sp',
                size_hint_x=0.25
            ))
            
            self.txn_content.add_widget(txn_widget)
    
    def _build_expiry_panel(self):
        """Build expiry management panel."""
        panel = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Actions
        action_box = BoxLayout(size_hint_y=0.15, spacing=10)
        
        btn_check = Button(
            text='Run Expiry Check',
            font_size='18sp',
            background_color=(0.8, 0.6, 0.2, 1)
        )
        btn_check.bind(on_press=self._run_expiry_check)
        action_box.add_widget(btn_check)
        
        btn_warnings = Button(
            text='Send Warnings',
            font_size='18sp',
            background_color=(0.2, 0.6, 0.8, 1)
        )
        btn_warnings.bind(on_press=self._send_expiry_warnings)
        action_box.add_widget(btn_warnings)
        
        panel.add_widget(action_box)
        
        # Expiring batches list
        scroll = ScrollView(size_hint=(1, 0.85))
        
        self.exp_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.exp_content.bind(minimum_height=self.exp_content.setter('height'))
        
        scroll.add_widget(self.exp_content)
        panel.add_widget(scroll)
        
        self._load_expiring_batches()
        
        return panel
    
    def _run_expiry_check(self, *args):
        """Run expiry check and confiscation."""
        result = self.expiry_mgr.daily_expiry_check(self.app.current_language)
        
        message = f"Expiry Check Complete:

"
        message += f"Warnings Sent: {result['warnings_sent']}
"
        message += f"Batches Confiscated: {result['confiscated']}
"
        
        self._show_info("Expiry Check", message)
        
        self._load_expiring_batches()
    
    def _send_expiry_warnings(self, *args):
        """Send expiry warnings."""
        count = self.expiry_mgr.send_expiry_warnings(self.app.current_language)
        self._show_info("Warnings Sent", f"Sent {count} expiry warnings via WhatsApp")
    
    def _load_expiring_batches(self):
        """Load expiring batches."""
        self.exp_content.clear_widgets()
        
        expiring = self.expiry_mgr.check_expiring_batches(warning_days=30)
        
        self.exp_content.add_widget(Label(
            text=f"[b]Batches Expiring in Next 30 Days: {len(expiring)}[/b]",
            markup=True,
            font_size='20sp',
            size_hint_y=None,
            height=40
        ))
        
        for batch in expiring:
            batch_widget = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=5)
            
            from kivy.graphics import Color, Rectangle
            with batch_widget.canvas.before:
                Color(1, 0.9, 0.9, 1)
                batch_widget.rect = Rectangle(size=batch_widget.size, pos=batch_widget.pos)
            
            batch_widget.bind(size=lambda obj, val: setattr(obj.rect, 'size', val))
            batch_widget.bind(pos=lambda obj, val: setattr(obj.rect, 'pos', val))
            
            batch_widget.add_widget(Label(
                text=f"[b]{batch['batch_code']}[/b] - {batch['farmer_name']}",
                markup=True,
                font_size='16sp',
                size_hint_y=0.4
            ))
            
            batch_widget.add_widget(Label(
                text=f"{batch['crop_type']} - {batch['weight_kg']:.2f}kg - Expires: {batch['expiry_date']}",
                font_size='14sp',
                size_hint_y=0.6
            ))
            
            self.exp_content.add_widget(batch_widget)
    
    def _build_system_panel(self):
        """Build system health panel."""
        panel = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # System info
        info = GridLayout(cols=2, spacing=10, size_hint_y=0.5)
        
        info.add_widget(Label(text='Godown ID:', font_size='18sp', bold=True))
        info.add_widget(Label(text=self.app.config.get('godown_id', 'N/A'), font_size='18sp'))
        
        info.add_widget(Label(text='Simulation Mode:', font_size='18sp', bold=True))
        sim_mode = 'YES' if self.app.config.get('simulation_mode') else 'NO'
        info.add_widget(Label(text=sim_mode, font_size='18sp', color=(1, 0, 0, 1) if sim_mode == 'YES' else (0, 1, 0, 1)))
        
        info.add_widget(Label(text='Total Capacity:', font_size='18sp', bold=True))
        info.add_widget(Label(text=f"{self.app.config['capacity']['total']} kg", font_size='18sp'))
        
        info.add_widget(Label(text='Current Stock:', font_size='18sp', bold=True))
        info.add_widget(Label(text=f"{self.inventory.get_total_stock():.2f} kg", font_size='18sp'))
        
        panel.add_widget(info)
        
        # Hardware health
        from hardware.hardware_manager import get_hardware
        hw = get_hardware()
        health = hw.get_health_status()
        
        health_box = BoxLayout(orientation='vertical', size_hint_y=0.3, padding=10)
        health_box.add_widget(Label(text='[b]Hardware Status:[/b]', markup=True, font_size='20sp', size_hint_y=0.3))
        
        for component, status in health.items():
            status_widget = BoxLayout(orientation='horizontal', size_hint_y=0.7/len(health))
            status_widget.add_widget(Label(text=f"{component.upper()}:", font_size='16sp'))
            
            color = (0, 1, 0, 1) if status == 'ok' else (1, 0, 0, 1)
            status_widget.add_widget(Label(text=status.upper(), font_size='16sp', color=color))
            
            health_box.add_widget(status_widget)
        
        panel.add_widget(health_box)
        
        # Actions
        action_box = BoxLayout(size_hint_y=0.2, spacing=10)
        
        btn_export = Button(
            text='Export Data',
            font_size='18sp',
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_export.bind(on_press=self._export_data)
        action_box.add_widget(btn_export)
        
        btn_vacuum = Button(
            text='Vacuum DB',
            font_size='18sp',
            background_color=(0.6, 0.6, 0.2, 1)
        )
        btn_vacuum.bind(on_press=self._vacuum_db)
        action_box.add_widget(btn_vacuum)
        
        panel.add_widget(action_box)
        
        return panel
    
    def _export_data(self, *args):
        """Export database to Excel (placeholder)."""
        # TODO: Implement Excel export using openpyxl
        self._show_info("Export", "Data export not yet implemented")
    
    def _vacuum_db(self, *args):
        """Vacuum database."""
        db.vacuum()
        self._show_info("Database", "Database vacuumed successfully")
    
    def _show_info(self, title, message):
        """Show info popup."""
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        content.add_widget(Label(text=message, font_size='18sp'))
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.6, 0.4)
        )
        
        btn_ok = Button(text='OK', font_size='18sp', size_hint_y=0.3)
        btn_ok.bind(on_press=popup.dismiss)
        content.add_widget(btn_ok)
        
        popup.open()
    
    def _on_logout(self, *args):
        """Logout and return to startup."""
        self.manager.current = 'startup' 