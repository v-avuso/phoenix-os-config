"""Run shared deployment and component checks; pass the installed Omd2Typst main.js."""
from pathlib import Path
import subprocess
import sys

module = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(module/'tests/deployment.py')], check=True)
subprocess.run([sys.executable, str(module/'templates/phoenix-letter/tests/run.py'), *sys.argv[1:]], check=True)
