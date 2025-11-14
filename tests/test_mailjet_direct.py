import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Mailjet SMTP settings
smtp_server = "in-v3.mailjet.com"
smtp_port = 587
username = "7a545957c5a1a63b98009a6fc9775950"
password = "77e7dd27f3709fa8adf99ddc7c8ee0fe"

# Email details
sender = "noreply@youarecoder.com"
recipient = "mustafa@alkedos.com"  # Without +
subject = "Direct Mailjet Test"
body = "This is a direct test from Mailjet SMTP"

# Create message
msg = MIMEMultipart()
msg['From'] = sender
msg['To'] = recipient
msg['Subject'] = subject
msg.attach(MIMEText(body, 'plain'))

try:
    # Connect and send
    print(f"Connecting to {smtp_server}:{smtp_port}...")
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    
    print("Logging in...")
    server.login(username, password)
    
    print(f"Sending email to {recipient}...")
    server.send_message(msg)
    
    print("✅ Email sent successfully!")
    server.quit()
    
except Exception as e:
    print(f"❌ Error: {e}")
