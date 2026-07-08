import sys
import os
import subprocess

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("Running Enterprise Test Suite...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
    
    # Run pytest with coverage
    cmd = ["python", "-m", "pytest", "tests/", "-v", "--cov=app", "--cov-report=term-missing"]
    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
