"""
Receipt Viewer Component
Display and print receipts.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.properties import DictProperty
import logging

logger = logging.getLogger(__name__)


class ReceiptViewer(BoxLayout):
    """Receipt display widget."""
    
    receipt_data = DictProperty({})
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 10
        
        # Receipt content
        self.scroll_view = ScrollView(size_hint=(1, 0.9))
        self.content_label = Label(
            text='',
            markup=True,
            font_size='16sp',
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        self.content_label.bind(texture_size=self.content_label.setter('size'))
        self.scroll_view.add_widget(self.content_label)
        self.add_widget(self.scroll_view)
        
        # Buttons
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        
        btn_print = Button(
            text='Print Receipt',
            font_size='18sp',
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_print.bind(on_press=self._on_print)
        btn_layout.add_widget(btn_print)
        
        btn_close = Button(
            text='Close',
            font_size='18sp',
            background_color=(0.6, 0.2, 0.2, 1)
        )
        btn_close.bind(on_press=self._on_close)
        btn_layout.add_widget(btn_close)
        
        self.add_widget(btn_layout)
    
    def show_receipt(self, receipt_data):
        """Display receipt."""
        self.receipt_data = receipt_data
        self.content_label.text = self._format_receipt(receipt_data)
    
    def _format_receipt(self, data):
        """Format receipt data as markup text."""
        if not data:
            return "[color=ff0000]No receipt data[/color]"
        
        # Header
        receipt = f"[size=24][b]{data.get('godown_name', 'Godown')}[/b][/size]"
        receipt += f"[size=18]{data.get('location', '')}[/size]"
        receipt += "=" * 50 + "
"
        
        # Receipt number and date
        receipt += f"[b]Receipt #:[/b] {data.get('receipt_number', 'N/A')}"
        receipt += f"[b]Date:[/b] {data.get('receipt_date', 'N/A')}"
        receipt += f"[b]Transaction:[/b] {data.get('txn_code', 'N/A')}
"
        
        # Farmer details
        receipt += "[b]Farmer Details:[/b]"
        receipt += f"  Name: {data.get('farmer_name', 'N/A')}"
        receipt += f"  Phone: {data.get('farmer_phone', 'N/A')}
"
        
        # Transaction details
        txn_type = data.get('txn_type', 'storage')
        receipt += f"[b]Transaction Type:[/b] {txn_type.upper()}"
        receipt += f"[b]Crop:[/b] {data.get('crop_type', 'N/A')}"
        receipt += f"[b]Weight:[/b] {data.get('weight_kg', 0)} kg"
        
        if data.get('batch_code'):
            receipt += f"[b]Batch Code:[/b] {data.get('batch_code', 'N/A')}"
        
        if data.get('quality_grade'):
            receipt += f"[b]Quality:[/b] Grade {data.get('quality_grade', 'N/A')}"
        
        if data.get('moisture_percent'):
            receipt += f"[b]Moisture:[/b] {data.get('moisture_percent', 0)}%"
        
        receipt += "" + "-" * 50 + "
"
        
        # Amount
        amount = data.get('amount', 0)
        if txn_type == 'storage':
            receipt += f"[size=20][b]Storage Fee: ₹{amount:.2f}[/b][/size]"
        elif txn_type == 'selling':
            receipt += f"[size=20][b]Amount Paid: ₹{amount:.2f}[/b][/size]"
        elif txn_type == 'buying':
            receipt += f"[size=20][b]Amount Received: ₹{amount:.2f}[/b][/size]"
        
        # Payment details
        receipt += f"[b]Payment Status:[/b] {data.get('payment_status', 'N/A')}"
        receipt += f"[b]Payment Method:[/b] {data.get('payment_method', 'N/A')}"
        
        if data.get('payment_ref'):
            receipt += f"[b]Payment Ref:[/b] {data.get('payment_ref', 'N/A')}"
        
        # Simulation notice
        if data.get('is_simulation'):
            receipt += "
[color=ff0000][b][size=18]*** SIMULATION ONLY ***[/size][/b][/color]"
        
        receipt += "" + "=" * 50 + ""
        receipt += "[b]Operator:[/b] " + data.get('operator_name', 'N/A') + ""
        receipt += "
Thank you for using our facility!"
        
        return receipt
    
    def _on_print(self, *args):
        """Print receipt (placeholder - would integrate with printer)."""
        logger.info("Print receipt requested")
        # TODO: Integrate with thermal printer or PDF generation
        print("" + "=" * 60)
        print("PRINTING RECEIPT (SIMULATION)")
        print("=" * 60)
        print(self.content_label.text.replace('[b]', '').replace('[/b]', '')
              .replace('[size=24]', '').replace('[size=18]', '').replace('[size=20]', '')
              .replace('[/size]', '').replace('[color=ff0000]', '').replace('[/color]', ''))
        print("=" * 60 + "")
    
    def _on_close(self, *args):
        """Close receipt viewer."""
        # In real app, would dismiss popup or change screen
        logger.info("Receipt viewer closed")