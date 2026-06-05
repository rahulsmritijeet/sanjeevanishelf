"""
WhatsApp Templates - Now formats SMS messages
Same file name, same function names, same interface.
Just shorter messages suited for SMS.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class WhatsAppTemplates:
    """
    SMS message templates.
    Same class name and method names as before.
    Nothing else in the codebase needs to change.
    """
    
    @staticmethod
    def format_message(template_name: str, language: str, data: Dict) -> str:
        """
        Format a message template.
        Same interface as before - called exactly the same way.
        """
        method_map = {
            'STORAGE_CONFIRMATION': WhatsAppTemplates._storage_confirmation,
            'SELLING_CONFIRMATION': WhatsAppTemplates._selling_confirmation,
            'EXPIRY_WARNING': WhatsAppTemplates._expiry_warning,
            'PAYMENT_REMINDER': WhatsAppTemplates._payment_reminder,
            'QUALITY_REJECTION': WhatsAppTemplates._quality_rejection,
        }
        
        method = method_map.get(template_name)
        
        if method:
            try:
                return method(data, language)
            except KeyError as e:
                logger.error(f"Missing template key {e} for {template_name}")
                return method(data, 'en')
        
        logger.error(f"Unknown template: {template_name}")
        return f"Godown Notification: {template_name}"
    
    @staticmethod
    def _storage_confirmation(data: Dict, language: str = 'en') -> str:
        """Storage confirmation SMS."""
        templates = {
            'en': (
                "STORAGE CONFIRMED\n"
                "{godown_name}\n"
                "Farmer: {farmer_name}\n"
                "Batch: {batch_code}\n"
                "Crop: {crop_type}\n"
                "Weight: {weight_kg}kg\n"
                "Grade: {quality_grade}\n"
                "Moisture: {moisture}%\n"
                "Fee: Rs.{amount}\n"
                "Payment: {payment_status}\n"
                "Expiry: {expiry_date}\n"
                "Location: {stack_location}\n"
                "RFID: {rfid_uid}"
            ),
            'hi': (
                "भंडारण पुष्टि\n"
                "{godown_name}\n"
                "किसान: {farmer_name}\n"
                "बैच: {batch_code}\n"
                "फसल: {crop_type}\n"
                "वजन: {weight_kg}किलो\n"
                "ग्रेड: {quality_grade}\n"
                "नमी: {moisture}%\n"
                "शुल्क: Rs.{amount}\n"
                "भुगतान: {payment_status}\n"
                "समाप्ति: {expiry_date}\n"
                "स्थान: {stack_location}"
            ),
            'bn': (
                "সংরক্ষণ নিশ্চিত\n"
                "{godown_name}\n"
                "কৃষক: {farmer_name}\n"
                "ব্যাচ: {batch_code}\n"
                "ফসল: {crop_type}\n"
                "ওজন: {weight_kg}কেজি\n"
                "গ্রেড: {quality_grade}\n"
                "আর্দ্রতা: {moisture}%\n"
                "ফি: Rs.{amount}\n"
                "পেমেন্ট: {payment_status}\n"
                "মেয়াদ: {expiry_date}\n"
                "অবস্থান: {stack_location}"
            )
        }
        template = templates.get(language, templates['en'])
        return template.format(**data)
    
    @staticmethod
    def _selling_confirmation(data: Dict, language: str = 'en') -> str:
        """Selling confirmation SMS."""
        templates = {
            'en': (
                "SALE COMPLETED\n"
                "{godown_name}\n"
                "Farmer: {farmer_name}\n"
                "Batch: {batch_code}\n"
                "Crop: {crop_type}\n"
                "Weight: {weight_kg}kg\n"
                "Rate: Rs.{rate}/kg\n"
                "Total: Rs.{amount}\n"
                "Payment: {payment_method}\n"
                "Txn: {txn_code}\n"
                "Date: {txn_date}\n"
                "Amount credited to account."
            ),
            'hi': (
                "बिक्री पूर्ण\n"
                "{godown_name}\n"
                "किसान: {farmer_name}\n"
                "फसल: {crop_type}\n"
                "वजन: {weight_kg}किलो\n"
                "दर: Rs.{rate}/किलो\n"
                "कुल: Rs.{amount}\n"
                "लेन-देन: {txn_code}\n"
                "राशि खाते में जमा होगी।"
            ),
            'bn': (
                "বিক্রয় সম্পন্ন\n"
                "{godown_name}\n"
                "কৃষক: {farmer_name}\n"
                "ফসল: {crop_type}\n"
                "ওজন: {weight_kg}কেজি\n"
                "হার: Rs.{rate}/কেজি\n"
                "মোট: Rs.{amount}\n"
                "লেনদেন: {txn_code}\n"
                "পরিমাণ অ্যাকাউন্টে জমা হবে।"
            )
        }
        template = templates.get(language, templates['en'])
        return template.format(**data)
    
    @staticmethod
    def _expiry_warning(data: Dict, language: str = 'en') -> str:
        """Expiry warning SMS."""
        templates = {
            'en': (
                "EXPIRY ALERT\n"
                "{godown_name}\n"
                "Farmer: {farmer_name}\n"
                "Batch: {batch_code}\n"
                "Crop: {crop_type}\n"
                "Weight: {weight_kg}kg\n"
                "Expiry: {expiry_date}\n"
                "Days Left: {days_remaining}\n"
                "Please collect/sell soon!\n"
                "Contact: {contact_number}"
            ),
            'hi': (
                "समाप्ति चेतावनी\n"
                "{godown_name}\n"
                "किसान: {farmer_name}\n"
                "बैच: {batch_code}\n"
                "फसल: {crop_type}\n"
                "शेष दिन: {days_remaining}\n"
                "समाप्ति: {expiry_date}\n"
                "जल्द संपर्क करें: {contact_number}"
            ),
            'bn': (
                "মেয়াদ সতর্কতা\n"
                "{godown_name}\n"
                "কৃষক: {farmer_name}\n"
                "ব্যাচ: {batch_code}\n"
                "ফসল: {crop_type}\n"
                "অবশিষ্ট দিন: {days_remaining}\n"
                "মেয়াদ: {expiry_date}\n"
                "যোগাযোগ: {contact_number}"
            )
        }
        template = templates.get(language, templates['en'])
        return template.format(**data)
    
    @staticmethod
    def _payment_reminder(data: Dict, language: str = 'en') -> str:
        """Payment reminder SMS."""
        templates = {
            'en': (
                "PAYMENT REMINDER\n"
                "{godown_name}\n"
                "Farmer: {farmer_name}\n"
                "Txn: {txn_code}\n"
                "Amount Due: Rs.{amount}\n"
                "Please pay at earliest.\n"
                "Contact: {contact_number}"
            ),
            'hi': (
                "भुगतान अनुस्मारक\n"
                "{godown_name}\n"
                "किसान: {farmer_name}\n"
                "बकाया: Rs.{amount}\n"
                "संपर्क: {contact_number}"
            ),
            'bn': (
                "পেমেন্ট রিমাইন্ডার\n"
                "{godown_name}\n"
                "কৃষক: {farmer_name}\n"
                "বকেয়া: Rs.{amount}\n"
                "যোগাযোগ: {contact_number}"
            )
        }
        template = templates.get(language, templates['en'])
        return template.format(**data)
    
    @staticmethod
    def _quality_rejection(data: Dict, language: str = 'en') -> str:
        """Quality rejection SMS."""
        templates = {
            'en': (
                "QUALITY REJECTED\n"
                "{godown_name}\n"
                "Farmer: {farmer_name}\n"
                "Crop: {crop_type}\n"
                "Weight: {weight_kg}kg\n"
                "Reason: {rejection_reason}\n"
                "Moisture: {moisture}%\n"
                "Max Allowed: {max_moisture}%\n"
                "Contact: {contact_number}"
            ),
            'hi': (
                "गुणवत्ता अस्वीकृत\n"
                "{godown_name}\n"
                "किसान: {farmer_name}\n"
                "कारण: {rejection_reason}\n"
                "नमी: {moisture}%\n"
                "संपर्क: {contact_number}"
            ),
            'bn': (
                "গুণমান প্রত্যাখ্যাত\n"
                "{godown_name}\n"
                "কৃষক: {farmer_name}\n"
                "কারণ: {rejection_reason}\n"
                "আর্দ্রতা: {moisture}%\n"
                "যোগাযোগ: {contact_number}"
            )
        }
        template = templates.get(language, templates['en'])
        return template.format(**data)