import traceback
import sys

try:
    from main import app
    print("SUCCESS")
except Exception as e:
    print("STARTUP_FAILED")
    traceback.print_exc()
    sys.exit(1)
