"""
Test Twilio SMS - Run this first to verify credentials
"""

from twilio.rest import Client

# PUT YOUR REAL CREDENTIALS HERE
ACCOUNT_SID = "AC66bf8e05de606a3200e758d376728ce1"
AUTH_TOKEN  = "af8d5aa2aeab12cdd725e441dac4ba13"
FROM_NUMBER = "+16084394908"   # Your Twilio number
TO_NUMBER   = "+917011811024"  # Your real phone number (with country code)


print("Testing Twilio SMS...")
print(f"From: {FROM_NUMBER}")
print(f"To:   {TO_NUMBER}")
print()

try:
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    
    # Verify account first
    account = client.api.accounts(ACCOUNT_SID).fetch()
    print(f"Account: {account.friendly_name}")
    print(f"Status:  {account.status}")
    print()
    
    # Send test SMS
    message = client.messages.create(
        body="TEST: Sanjeevani Shelf SMS working! Godown system test.",
        from_=FROM_NUMBER,
        to=TO_NUMBER
    )
    
    print(f"SUCCESS!")
    print(f"SID:    {message.sid}")
    print(f"Status: {message.status}")
    print(f"Check your phone!")

except Exception as e:
    print(f"FAILED: {e}")
    print()
    print("Common fixes:")
    print("1. Check Account SID and Auth Token")
    print("2. Verify your Twilio phone number")
    print("3. On free trial - verify recipient number at:")
    print("   https://console.twilio.com/us1/develop/phone-numbers/manage/verified")