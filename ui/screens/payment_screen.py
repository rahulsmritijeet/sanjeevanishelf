"""
Payment Screen - PyQt5
Split payment: UPI, Cash, UPI+Cash
Cash limit: Max 2000
QR code, rate breakdown, 5-minute timer.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QFrame, QScrollArea, QLineEdit, QDialog
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime
import logging
from payment.razorpay_handler import RazorpayHandler
from payment.payment_simulation import PaymentSimulator
from database.db_manager import db

logger = logging.getLogger(__name__)

MAX_CASH_LIMIT = 2000


class PaymentScreen(QWidget):
    """Payment screen with split payment support."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        self.razorpay = RazorpayHandler(
            app.app_config,
            simulation=not bool(app.app_config.get('razorpay', {}).get('key_id'))
        )
        self.payment_sim = PaymentSimulator()
        
        self.amount = 0
        self.cash_amount = 0
        self.upi_amount = 0
        self.payment_mode = 'upi'
        self.transaction_type = 'storage'
        self.flow_data = {}
        self.farmer = None
        self.session = None
        self.batch = None
        self.on_complete_callback = None
        
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._update_session_timer)
    
    def setup_payment(self, amount, transaction_type='storage', flow_data=None,
                     farmer=None, session=None, batch=None, on_complete=None):
        """Setup payment screen."""
        self.amount = amount
        self.cash_amount = 0
        self.upi_amount = amount
        self.payment_mode = 'upi'
        self.transaction_type = transaction_type
        self.flow_data = flow_data or {}
        self.farmer = farmer
        self.session = session
        self.batch = batch
        self.on_complete_callback = on_complete
        
        self._clear_layout()
        self._session_timer.start(1000)
        self._show_payment_method_selection()
    
    def _clear_layout(self):
        """Clear all widgets from layout."""
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    item = child.layout().takeAt(0)
                    if item and item.widget():
                        item.widget().deleteLater()
    
    def _add_header(self, title_text):
        """Add standard header with timer and cancel."""
        header = QHBoxLayout()
        
        title = QLabel(title_text)
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        title.setFont(tf)
        header.addWidget(title, stretch=1)
        
        self.timer_label = QLabel('⏱ 05:00')
        tmf = QFont()
        tmf.setPointSize(14)
        tmf.setBold(True)
        self.timer_label.setFont(tmf)
        self.timer_label.setStyleSheet("color: green;")
        header.addWidget(self.timer_label)
        
        btn_cancel = QPushButton('✗ Cancel')
        btn_cancel.setFixedWidth(90)
        btn_cancel.setFixedHeight(35)
        btn_cancel.setStyleSheet("background-color: #F44336; color: white;")
        btn_cancel.clicked.connect(self._cancel_session)
        header.addWidget(btn_cancel)
        
        self.main_layout.addLayout(header)
    
    def _add_amount_display(self, text, color="#2E7D32", bg="#E8F5E9", border="#4CAF50"):
        """Add amount display frame."""
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setStyleSheet(f"background-color: {bg}; border: 2px solid {border}; border-radius: 5px;")
        layout = QVBoxLayout()
        
        label = QLabel(text)
        lf = QFont()
        lf.setPointSize(20)
        lf.setBold(True)
        label.setFont(lf)
        label.setStyleSheet(f"color: {color};")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        frame.setLayout(layout)
        frame.setFixedHeight(70)
        self.main_layout.addWidget(frame)
    
    def _add_farmer_info(self):
        """Add farmer info bar."""
        if not self.farmer:
            return
        
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setStyleSheet("background-color: #F5F5F5; border: 1px solid #DDD; border-radius: 3px;")
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel(f"Farmer: {self.farmer['name']}"))
        layout.addWidget(QLabel(f"Phone: {self.farmer['phone']}"))
        
        if self.farmer.get('village'):
            layout.addWidget(QLabel(f"Village: {self.farmer['village']}"))
        
        frame.setLayout(layout)
        frame.setFixedHeight(40)
        self.main_layout.addWidget(frame)
    
    def _add_rate_breakdown(self):
        """Add rate breakdown section."""
        breakdown = self.flow_data.get('billing_breakdown', {})
        if not breakdown:
            return
        
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setStyleSheet("background-color: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 3px;")
        layout = QVBoxLayout()
        
        rt = QLabel('Rate Breakdown')
        rt.setFont(QFont('Arial', 11, QFont.Bold))
        layout.addWidget(rt)
        
        weight = self.flow_data.get('weight_kg', 0)
        
        if self.transaction_type == 'storage':
            rate = breakdown.get('rate_per_kg_per_month',
                self.app.app_config.get('billing', {}).get('storage_rate_per_kg_per_month', 2.0))
            duration = breakdown.get('duration_months', 1.0)
            base_fee = breakdown.get('base_fee', self.amount)
            quality_adj = breakdown.get('quality_adjustment', 0)
            grade = self.flow_data.get('quality_grade', 'B')
            
            layout.addWidget(QLabel(f"   Rate: Rs.{rate:.2f}/kg/month"))
            layout.addWidget(QLabel(f"   Weight: {weight:.2f} kg x {duration:.1f} month"))
            layout.addWidget(QLabel(f"   Base Fee: Rs.{base_fee:.2f}"))
            
            if quality_adj != 0:
                adj_type = "Premium" if quality_adj > 0 else "Penalty"
                ql = QLabel(f"   Quality {adj_type} (Grade {grade}): Rs.{quality_adj:.2f}")
                ql.setStyleSheet("color: green;" if quality_adj > 0 else "color: red;")
                layout.addWidget(ql)
        
        elif self.transaction_type == 'selling':
            base_rate = breakdown.get('base_rate', 0)
            quality_multiplier = breakdown.get('quality_multiplier', 1.0)
            base_amount = breakdown.get('base_amount', 0)
            adjusted_amount = breakdown.get('adjusted_amount', 0)
            
            layout.addWidget(QLabel(f"   Market Rate: Rs.{base_rate:.2f}/kg"))
            layout.addWidget(QLabel(f"   Weight: {weight:.2f} kg"))
            layout.addWidget(QLabel(f"   Base: Rs.{base_amount:.2f}"))
            
            if quality_multiplier != 1.0:
                qp = (quality_multiplier - 1.0) * 100
                ql = QLabel(f"   Quality {'Premium' if qp > 0 else 'Penalty'}: {qp:+.0f}%")
                ql.setStyleSheet("color: green;" if qp > 0 else "color: red;")
                layout.addWidget(ql)
                layout.addWidget(QLabel(f"   Adjusted: Rs.{adjusted_amount:.2f}"))
        
        elif self.transaction_type == 'buying':
            market_rate = breakdown.get('market_rate', 0)
            msp_rate = breakdown.get('msp_rate', 0)
            applied_rate = breakdown.get('applied_rate', 0)
            quality_multiplier = breakdown.get('quality_multiplier', 1.0)
            
            layout.addWidget(QLabel(f"   Market Rate: Rs.{market_rate:.2f}/kg"))
            layout.addWidget(QLabel(f"   MSP Rate: Rs.{msp_rate:.2f}/kg"))
            al = QLabel(f"   Applied: Rs.{applied_rate:.2f}/kg (Higher rate)")
            al.setStyleSheet("color: #0066CC; font-weight: bold;")
            layout.addWidget(al)
            layout.addWidget(QLabel(f"   Weight: {weight:.2f} kg"))
            
            if quality_multiplier != 1.0:
                qp = (quality_multiplier - 1.0) * 100
                ql = QLabel(f"   Quality {'Premium' if qp > 0 else 'Penalty'}: {qp:+.0f}%")
                ql.setStyleSheet("color: green;" if qp > 0 else "color: red;")
                layout.addWidget(ql)
        
        # Total
        layout.addWidget(QLabel('   ' + '-' * 35))
        tl = QLabel(f"   TOTAL: Rs.{self.amount:.2f}")
        tl.setFont(QFont('Arial', 13, QFont.Bold))
        tl.setStyleSheet("color: #2E7D32;")
        layout.addWidget(tl)
        
        frame.setLayout(layout)
        self.main_layout.addWidget(frame)
    
    def _show_payment_method_selection(self):
        """Show payment method selection."""
        self._clear_layout()
        
        # Header
        if self.transaction_type == 'storage':
            self._add_header('Payment - Storage Fee')
        elif self.transaction_type == 'selling':
            self._add_header('Payout - Selling')
        else:
            self._add_header('Payment - Buying')
        
        # Amount
        self._add_amount_display(f'Total: Rs.{self.amount:.2f}')
        
        # Farmer info
        self._add_farmer_info()
        
        # Rate breakdown
        self._add_rate_breakdown()
        
        # Payment method frame
        method_frame = QFrame()
        method_frame.setFrameShape(QFrame.Box)
        method_frame.setStyleSheet("background-color: #FFF8E1; border: 2px solid #FFC107; border-radius: 5px;")
        method_layout = QVBoxLayout()
        
        method_title = QLabel('Select Payment Method')
        method_title.setFont(QFont('Arial', 14, QFont.Bold))
        method_layout.addWidget(method_title)
        
        if self.amount > MAX_CASH_LIMIT:
            # Amount > 2000: UPI or UPI+Cash
            notice = QLabel(f'Cash payments limited to Rs.{MAX_CASH_LIMIT}')
            notice.setStyleSheet("color: red; font-weight: bold;")
            method_layout.addWidget(notice)
            
            method_layout.addSpacing(10)
            
            btn_upi = QPushButton(f'UPI - Full Amount Rs.{self.amount:.2f}')
            btn_upi.setFixedHeight(60)
            btn_upi.setFont(QFont('Arial', 12, QFont.Bold))
            btn_upi.setStyleSheet("background-color: #2196F3; color: white; border-radius: 5px;")
            btn_upi.clicked.connect(lambda: self._select_mode('upi'))
            method_layout.addWidget(btn_upi)
            
            method_layout.addSpacing(10)
            
            btn_split = QPushButton(f'UPI + Cash (Cash max Rs.{MAX_CASH_LIMIT})')
            btn_split.setFixedHeight(60)
            btn_split.setFont(QFont('Arial', 12, QFont.Bold))
            btn_split.setStyleSheet("background-color: #FF9800; color: white; border-radius: 5px;")
            btn_split.clicked.connect(lambda: self._select_mode('upi_cash'))
            method_layout.addWidget(btn_split)
        
        else:
            # Amount <= 2000: UPI or Cash
            btn_upi = QPushButton(f'UPI - Rs.{self.amount:.2f}')
            btn_upi.setFixedHeight(60)
            btn_upi.setFont(QFont('Arial', 12, QFont.Bold))
            btn_upi.setStyleSheet("background-color: #2196F3; color: white; border-radius: 5px;")
            btn_upi.clicked.connect(lambda: self._select_mode('upi'))
            method_layout.addWidget(btn_upi)
            
            method_layout.addSpacing(10)
            
            btn_cash = QPushButton(f'Cash - Rs.{self.amount:.2f}')
            btn_cash.setFixedHeight(60)
            btn_cash.setFont(QFont('Arial', 12, QFont.Bold))
            btn_cash.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px;")
            btn_cash.clicked.connect(lambda: self._select_mode('cash'))
            method_layout.addWidget(btn_cash)
        
        method_frame.setLayout(method_layout)
        self.main_layout.addWidget(method_frame, stretch=1)
        
        # Back button
        btn_back = QPushButton('Back to Summary')
        btn_back.setFixedHeight(40)
        btn_back.setStyleSheet("background-color: #757575; color: white;")
        btn_back.clicked.connect(self._on_back)
        self.main_layout.addWidget(btn_back)
    
    def _select_mode(self, mode):
        """Handle payment mode selection."""
        self.payment_mode = mode
        
        if mode == 'upi':
            self.upi_amount = self.amount
            self.cash_amount = 0
            self._show_upi_screen()
        elif mode == 'cash':
            self.cash_amount = self.amount
            self.upi_amount = 0
            self._show_cash_screen()
        elif mode == 'upi_cash':
            self._show_cash_entry_dialog()
    
    def _show_cash_entry_dialog(self):
        """Dialog to enter cash amount for split payment."""
        dialog = QDialog(self)
        dialog.setWindowTitle('Enter Cash Amount')
        dialog.setGeometry(150, 100, 400, 350)
        dialog.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel(f'Total Amount: Rs.{self.amount:.2f}'))
        layout.addWidget(QLabel(f'Enter cash amount (max Rs.{MAX_CASH_LIMIT}):'))
        
        cash_input = QLineEdit()
        cash_input.setFont(QFont('Arial', 18))
        cash_input.setFixedHeight(50)
        cash_input.setPlaceholderText(f'Max Rs.{MAX_CASH_LIMIT}')
        layout.addWidget(cash_input)
        
        remaining_label = QLabel(f'Remaining via UPI: Rs.{self.amount:.2f}')
        remaining_label.setFont(QFont('Arial', 12, QFont.Bold))
        remaining_label.setStyleSheet("color: #2196F3;")
        layout.addWidget(remaining_label)
        
        status = QLabel('')
        status.setStyleSheet("color: red;")
        layout.addWidget(status)
        
        def update_remaining():
            try:
                cash = float(cash_input.text()) if cash_input.text() else 0
                remaining = self.amount - cash
                remaining_label.setText(f'Remaining via UPI: Rs.{remaining:.2f}')
                
                if cash > MAX_CASH_LIMIT:
                    status.setText(f'Cash cannot exceed Rs.{MAX_CASH_LIMIT}!')
                    remaining_label.setStyleSheet("color: red;")
                elif cash < 0 or remaining < 0:
                    status.setText('Invalid amount!')
                    remaining_label.setStyleSheet("color: red;")
                else:
                    status.setText('')
                    remaining_label.setStyleSheet("color: #2196F3;")
            except ValueError:
                status.setText('Enter a valid number')
        
        cash_input.textChanged.connect(update_remaining)
        
        btn_layout = QHBoxLayout()
        
        def on_proceed():
            try:
                cash = float(cash_input.text()) if cash_input.text() else 0
            except ValueError:
                status.setText('Enter a valid number')
                return
            
            if cash > MAX_CASH_LIMIT:
                status.setText(f'Cash cannot exceed Rs.{MAX_CASH_LIMIT}!')
                return
            if cash <= 0:
                status.setText('Enter a positive amount')
                return
            if cash > self.amount:
                status.setText('Cash exceeds total!')
                return
            
            self.cash_amount = cash
            self.upi_amount = self.amount - cash
            dialog.accept()
            self._show_cash_collection()
        
        btn_ok = QPushButton('Proceed')
        btn_ok.setFixedHeight(50)
        btn_ok.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_ok.clicked.connect(on_proceed)
        btn_layout.addWidget(btn_ok)
        
        btn_no = QPushButton('Cancel')
        btn_no.setFixedHeight(50)
        btn_no.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_no)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        
        if dialog.exec_() != QDialog.Accepted:
            self._show_payment_method_selection()
    
    def _show_cash_collection(self):
        """Show cash collection screen for split payment."""
        self._clear_layout()
        self._add_header('Collect Cash')
        
        self._add_amount_display(
            f'Collect Cash: Rs.{self.cash_amount:.2f}',
            color="#2E7D32", bg="#E8F5E9", border="#4CAF50"
        )
        
        if self.upi_amount > 0:
            upi_label = QLabel(f'Remaining via UPI: Rs.{self.upi_amount:.2f}')
            upi_label.setFont(QFont('Arial', 14))
            upi_label.setStyleSheet("color: #1565C0;")
            upi_label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(upi_label)
        
        breakdown = QLabel(
            f'Total: Rs.{self.amount:.2f}\n'
            f'Cash: Rs.{self.cash_amount:.2f}\n'
            f'UPI: Rs.{self.upi_amount:.2f}'
        )
        breakdown.setFont(QFont('Arial', 12))
        breakdown.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(breakdown)
        
        self.main_layout.addStretch(1)
        
        btn_text = f'Cash Rs.{self.cash_amount:.2f} Received'
        if self.upi_amount > 0:
            btn_text += f' - Proceed to UPI Rs.{self.upi_amount:.2f}'
        
        btn_received = QPushButton(btn_text)
        btn_received.setFixedHeight(70)
        btn_received.setFont(QFont('Arial', 12, QFont.Bold))
        btn_received.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px;")
        btn_received.clicked.connect(self._on_cash_received)
        self.main_layout.addWidget(btn_received)
        
        btn_back = QPushButton('Back')
        btn_back.setFixedHeight(40)
        btn_back.setStyleSheet("background-color: #757575; color: white;")
        btn_back.clicked.connect(self._show_payment_method_selection)
        self.main_layout.addWidget(btn_back)
    
    def _on_cash_received(self):
        """Cash collected."""
        if self.upi_amount > 0:
            self._show_upi_screen()
        else:
            self._complete_payment('cash')
    
    def _show_cash_screen(self):
        """Full cash payment screen."""
        self._clear_layout()
        self._add_header('Cash Payment')
        
        self._add_amount_display(f'Collect Cash: Rs.{self.amount:.2f}')
        self._add_farmer_info()
        
        self.main_layout.addStretch(1)
        
        btn = QPushButton(f'PAYMENT RECEIVED  Rs.{self.amount:.2f}')
        btn.setFixedHeight(70)
        btn.setFont(QFont('Arial', 14, QFont.Bold))
        btn.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px;")
        btn.clicked.connect(lambda: self._complete_payment('cash'))
        self.main_layout.addWidget(btn)
        
        btn_back = QPushButton('Back')
        btn_back.setFixedHeight(40)
        btn_back.setStyleSheet("background-color: #757575; color: white;")
        btn_back.clicked.connect(self._show_payment_method_selection)
        self.main_layout.addWidget(btn_back)
    
    def _show_upi_screen(self):
        """UPI payment screen with QR."""
        self._clear_layout()
        
        upi_amount = self.upi_amount if self.upi_amount > 0 else self.amount
        
        self._add_header('UPI Payment')
        
        # Amount
        amount_text = f'UPI Amount: Rs.{upi_amount:.2f}'
        self._add_amount_display(amount_text, color="#1565C0", bg="#E3F2FD", border="#2196F3")
        
        # Cash already collected notice
        if self.cash_amount > 0:
            notice = QLabel(f'Cash Rs.{self.cash_amount:.2f} already collected')
            notice.setStyleSheet("color: #4CAF50; font-weight: bold;")
            notice.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(notice)
        
        # QR Code
        qr_frame = QFrame()
        qr_frame.setFrameShape(QFrame.Box)
        qr_frame.setStyleSheet("background-color: white; border: 2px solid #CCC; border-radius: 5px;")
        qr_layout = QVBoxLayout()
        
        qr_title = QLabel('Scan QR Code to Pay via UPI')
        qr_title.setFont(QFont('Arial', 11))
        qr_title.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(qr_title)
        
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self._generate_qr(upi_amount)
        qr_layout.addWidget(self.qr_label)
        
        qr_frame.setLayout(qr_layout)
        qr_frame.setFixedHeight(240)
        self.main_layout.addWidget(qr_frame, stretch=1)
        
        # Done button
        if self.transaction_type == 'storage':
            btn_text = f'PAYMENT DONE  Rs.{upi_amount:.2f}  (SIMULATION)'
            btn_color = "#4CAF50"
        else:
            btn_text = f'PAYOUT DONE  Rs.{upi_amount:.2f}  (SIMULATION)'
            btn_color = "#FF9800"
        
        btn_done = QPushButton(btn_text)
        btn_done.setFixedHeight(70)
        btn_done.setFont(QFont('Arial', 13, QFont.Bold))
        btn_done.setStyleSheet(f"background-color: {btn_color}; color: white; border-radius: 5px;")
        btn_done.clicked.connect(lambda: self._complete_payment('upi'))
        self.main_layout.addWidget(btn_done)
        
        # Back
        btn_back = QPushButton('Back')
        btn_back.setFixedHeight(40)
        btn_back.setStyleSheet("background-color: #757575; color: white;")
        btn_back.clicked.connect(self._show_payment_method_selection)
        self.main_layout.addWidget(btn_back)
    
    def _generate_qr(self, amount):
        """Generate and show QR code."""
        txn_id = f"TXN-{int(datetime.now().timestamp())}"
        
        try:
            upi_string, qr_bytes = self.razorpay.create_qr_code(
                amount, txn_id,
                f"{self.transaction_type.title()} Payment"
            )
            
            if qr_bytes:
                pixmap = QPixmap()
                pixmap.loadFromData(qr_bytes)
                pixmap = pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.qr_label.setPixmap(pixmap)
            else:
                self.qr_label.setText(f"[QR Code]\nAmount: Rs.{amount:.2f}\nTxn: {txn_id}")
        except Exception as e:
            logger.error(f"QR error: {e}")
            self.qr_label.setText(f"[QR Failed]\nAmount: Rs.{amount:.2f}")
    
    def _complete_payment(self, method):
        """Complete payment and trigger callback."""
        self._session_timer.stop()
        
        # Build payment method string
        if self.cash_amount > 0 and self.upi_amount > 0:
            payment_method = f"split_cash_{self.cash_amount}_upi_{self.upi_amount}"
        elif method == 'cash':
            payment_method = 'cash'
        else:
            payment_method = 'upi'
        
        logger.info(f"Payment complete - Method: {payment_method}, Total: Rs.{self.amount}")
        logger.info(f"  Cash: Rs.{self.cash_amount}, UPI: Rs.{self.upi_amount}")
        
        # Simulate payment
        if self.transaction_type in ['selling', 'buying']:
            farmer_id = self.farmer['id'] if self.farmer else 0
            success, ref = self.payment_sim.simulate_payout_sent(
                transaction_id=0,
                farmer_id=farmer_id,
                amount=self.amount,
                bank_account=self.farmer.get('bank_account', 'XXXX') if self.farmer else 'XXXX'
            )
        else:
            success, ref = self.payment_sim.simulate_payment_received(
                transaction_id=0,
                amount=self.amount,
                payment_method=payment_method
            )
        
        if success and self.on_complete_callback:
            self.on_complete_callback(ref)
        elif not success:
            QMessageBox.critical(self, 'Error', 'Payment processing failed!')
    
    def _update_session_timer(self):
        """Update timer."""
        if self.session and hasattr(self.session, 'get_time_display'):
            time_str = self.session.get_time_display()
            if hasattr(self, 'timer_label'):
                self.timer_label.setText(f"timer {time_str}")
                
                remaining = self.session.get_remaining_time()
                if remaining <= 60:
                    self.timer_label.setStyleSheet("color: red; font-weight: bold;")
                elif remaining <= 120:
                    self.timer_label.setStyleSheet("color: orange; font-weight: bold;")
                else:
                    self.timer_label.setStyleSheet("color: green; font-weight: bold;")
                
                if self.session.is_expired():
                    self._on_session_timeout()
    
    def _on_session_timeout(self):
        """Handle timeout."""
        self._session_timer.stop()
        QMessageBox.critical(self, "Session Timeout",
            "5-minute session expired!\nAll changes rolled back.")
        self.app.show_screen('startup')
    
    def _cancel_session(self):
        """Cancel session."""
        reply = QMessageBox.question(self, 'Cancel',
            'Cancel session? All changes lost.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self._session_timer.stop()
            if self.session:
                self.session.cancel()
            self.app.show_screen('startup')
    
    def _on_back(self):
        """Go back."""
        self._session_timer.stop()
        if self.transaction_type == 'storage':
            self.app.show_screen('storage')
        elif self.transaction_type == 'selling':
            self.app.show_screen('selling')
        elif self.transaction_type == 'buying':
            self.app.show_screen('buying')