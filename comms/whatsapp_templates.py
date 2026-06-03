"""
WhatsApp Message Templates with Multi-language Support
"""

from typing import Dict, Any


class WhatsAppTemplates:
    """Message templates for all WhatsApp notifications."""
    
    # Storage Confirmation
    STORAGE_CONFIRMATION = {
        'en': """✅ Storage Confirmed - {godown_name}

Farmer: {farmer_name}
Batch: {batch_code}
Crop: {crop_type}
Weight: {weight_kg} kg
Quality: Grade {quality_grade}
Moisture: {moisture}%

Storage Fee: ₹{amount}
Payment: {payment_status}

Valid until: {expiry_date}

RFID: {rfid_uid}
Location: {stack_location}

Thank you for using our facility!""",
        
        'hi': """✅ भंडारण पुष्टि - {godown_name}

किसान: {farmer_name}
बैच: {batch_code}
फसल: {crop_type}
वजन: {weight_kg} किलो
गुणवत्ता: ग्रेड {quality_grade}
नमी: {moisture}%

भंडारण शुल्क: ₹{amount}
भुगतान: {payment_status}

मान्य तिथि: {expiry_date}

RFID: {rfid_uid}
स्थान: {stack_location}

हमारी सुविधा का उपयोग करने के लिए धन्यवाद!""",
        
        'bn': """✅ সংরক্ষণ নিশ্চিত - {godown_name}

কৃষক: {farmer_name}
ব্যাচ: {batch_code}
ফসল: {crop_type}
ওজন: {weight_kg} কেজি
গুণমান: গ্রেড {quality_grade}
আর্দ্রতা: {moisture}%

সংরক্ষণ ফি: ₹{amount}
পেমেন্ট: {payment_status}

বৈধ তারিখ: {expiry_date}

RFID: {rfid_uid}
অবস্থান: {stack_location}

আমাদের সুবিধা ব্যবহারের জন্য ধন্যবাদ!"""
    }
    
    # Selling Confirmation
    SELLING_CONFIRMATION = {
        'en': """💰 Sale Completed - {godown_name}

Farmer: {farmer_name}
Batch: {batch_code}
Crop: {crop_type}
Weight: {weight_kg} kg
Rate: ₹{rate}/kg

Total Amount: ₹{amount}
Payment Mode: {payment_method}

Transaction: {txn_code}
Date: {txn_date}

Amount will be credited to your account.
Thank you!""",
        
        'hi': """💰 बिक्री पूर्ण - {godown_name}

किसान: {farmer_name}
बैच: {batch_code}
फसल: {crop_type}
वजन: {weight_kg} किलो
दर: ₹{rate}/किलो

कुल राशि: ₹{amount}
भुगतान मोड: {payment_method}

लेन-देन: {txn_code}
तारीख: {txn_date}

राशि आपके खाते में जमा की जाएगी।
धन्यवाद!""",
        
        'bn': """💰 বিক্রয় সম্পন্ন - {godown_name}

কৃষক: {farmer_name}
ব্যাচ: {batch_code}
ফসল: {crop_type}
ওজন: {weight_kg} কেজি
হার: ₹{rate}/কেজি

মোট পরিমাণ: ₹{amount}
পেমেন্ট মোড: {payment_method}

লেনদেন: {txn_code}
তারিখ: {txn_date}

পরিমাণ আপনার অ্যাকাউন্টে জমা হবে।
ধন্যবাদ!"""
    }
    
    # Expiry Warning
    EXPIRY_WARNING = {
        'en': """⚠️ Expiry Alert - {godown_name}

Farmer: {farmer_name}
Batch: {batch_code}
Crop: {crop_type}
Weight: {weight_kg} kg

Expiry Date: {expiry_date}
Days Remaining: {days_remaining}

Please collect or sell your stock soon.
Contact: {contact_number}""",
        
        'hi': """⚠️ समाप्ति चेतावनी - {godown_name}

किसान: {farmer_name}
बैच: {batch_code}
फसल: {crop_type}
वजन: {weight_kg} किलो

समाप्ति तिथि: {expiry_date}
शेष दिन: {days_remaining}

कृपया जल्द ही अपना स्टॉक एकत्र या बेचें।
संपर्क: {contact_number}""",
        
        'bn': """⚠️ মেয়াদ সতর্কতা - {godown_name}

কৃষক: {farmer_name}
ব্যাচ: {batch_code}
ফসল: {crop_type}
ওজন: {weight_kg} কেজি

মেয়াদ শেষের তারিখ: {expiry_date}
অবশিষ্ট দিন: {days_remaining}

দয়া করে শীঘ্রই আপনার স্টক সংগ্রহ বা বিক্রয় করুন।
যোগাযোগ: {contact_number}"""
    }
    
    # Payment Reminder
    PAYMENT_REMINDER = {
        'en': """💳 Payment Reminder - {godown_name}

Farmer: {farmer_name}
Transaction: {txn_code}
Amount Due: ₹{amount}

Please complete payment at the earliest.
Penalty applies after due date.

Contact: {contact_number}""",
        
        'hi': """💳 भुगतान अनुस्मारक - {godown_name}

किसान: {farmer_name}
लेन-देन: {txn_code}
बकाया राशि: ₹{amount}

कृपया जल्द से जल्द भुगतान पूरा करें।
नियत तारीख के बाद जुर्माना लागू होता है।

संपर्क: {contact_number}""",
        
        'bn': """💳 পেমেন্ট রিমাইন্ডার - {godown_name}

কৃষক: {farmer_name}
লেনদেন: {txn_code}
বকেয়া পরিমাণ: ₹{amount}

দয়া করে যত তাড়াতাড়ি সম্ভব পেমেন্ট সম্পূর্ণ করুন।
নির্ধারিত তারিখের পরে জরিমানা প্রযোজ্য।

যোগাযোগ: {contact_number}"""
    }
    
    # Quality Rejection
    QUALITY_REJECTION = {
        'en': """❌ Quality Check Failed - {godown_name}

Farmer: {farmer_name}
Crop: {crop_type}
Weight: {weight_kg} kg

Rejection Reason: {rejection_reason}
Moisture: {moisture}% (Max allowed: {max_moisture}%)

Your stock cannot be accepted.
Please contact us for options.

Contact: {contact_number}""",
        
        'hi': """❌ गुणवत्ता जांच विफल - {godown_name}

किसान: {farmer_name}
फसल: {crop_type}
वजन: {weight_kg} किलो

अस्वीकृति कारण: {rejection_reason}
नमी: {moisture}% (अधिकतम अनुमत: {max_moisture}%)

आपका स्टॉक स्वीकार नहीं किया जा सकता।
कृपया विकल्पों के लिए हमसे संपर्क करें।

संपर्क: {contact_number}""",
        
        'bn': """❌ গুণমান পরীক্ষা ব্যর্থ - {godown_name}

কৃষক: {farmer_name}
ফসল: {crop_type}
ওজন: {weight_kg} কেজি

প্রত্যাখ্যানের কারণ: {rejection_reason}
আর্দ্রতা: {moisture}% (সর্বোচ্চ অনুমোদিত: {max_moisture}%)

আপনার স্টক গ্রহণ করা যাবে না।
বিকল্পের জন্য আমাদের সাথে যোগাযোগ করুন।

যোগাযোগ: {contact_number}"""
    }
    
    @staticmethod
    def format_message(template_name: str, language: str, data: Dict[str, Any]) -> str:
        """Format a message template with given data."""
        templates = getattr(WhatsAppTemplates, template_name, None)
        
        if not templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        if language not in templates:
            language = 'en'  # Fallback to English
        
        template = templates[language]
        
        try:
            return template.format(**data)
        except KeyError as e:
            raise ValueError(f"Missing data for template {template_name}: {e}")