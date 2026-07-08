import traceback
import sys

try:
    from app.api.v1.endpoints import auth
    print("SUCCESS")
except Exception as e:
    print("STARTUP_FAILED")
    traceback.print_exc()
    sys.exit(1)
