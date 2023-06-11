import signal
import sys
import time

def handle_sigterm(*args):
    print("Received SIGTERM signal. Beginning graceful shutdown.")
    for i in range(45, 0, -1):
        print(f"Graceful shutdown in progress. Time remaining: {i} seconds.")
        time.sleep(1)
    print("Finished graceful shutdown.")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

while True:
    print("Running...")
    time.sleep(1)
