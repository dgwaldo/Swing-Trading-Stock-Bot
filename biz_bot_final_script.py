import subprocess
import sys
import time
from pathlib import Path

script_dir = Path(__file__).resolve().parent
venv_python = script_dir / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
python_executable = str(venv_python) if venv_python.is_file() else sys.executable

while True: # continually run through buy and sell scripts
        subprocess.run([python_executable, str(script_dir / 'biz_bot_place_orders.py')], cwd=script_dir, check=True)
        subprocess.run([python_executable, str(script_dir / 'biz_bot_sell.py')], cwd=script_dir, check=True)
        #print('waiting two minutes')
        time.sleep(60)
        print("-"*50)
        continue
