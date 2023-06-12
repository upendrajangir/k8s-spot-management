import signal
import sys
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


def handle_sigterm(*args):
    logging.info("Received SIGTERM signal. Beginning graceful shutdown.")
    for i in range(45, 0, -1):
        logging.info(f"Graceful shutdown in progress. Time remaining: {i} seconds.")
        time.sleep(1)
    logging.info("Finished graceful shutdown.")
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_sigterm)

while True:
    logging.info("Running...")
    time.sleep(1)
