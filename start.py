import os
import time

while True:
    exit_code = os.system("python3 main.py")
    if exit_code != 0:
        print("⚠️ Bot crashed! Restarting in 5 seconds...")
        time.sleep(5)
    else:
        print("✅ Bot stopped gracefully.")
        break
