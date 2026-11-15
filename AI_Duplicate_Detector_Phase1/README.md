# AI-Based Intelligent Duplicate File Detection System

## Phase 1: Setup and desktop application shell

### Requirements
- Windows 10/11
- Python 3.10 or newer (Python 3.11 recommended)
- PyCharm

### Create and activate a virtual environment
Open the PyCharm Terminal in this project folder and run:

```powershell
py -3.11 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use the PyCharm terminal configured as Command Prompt, then run:

```cmd
.venv\\Scripts\\activate.bat
```

### Run
```powershell
python main.py
```

The first phase creates the PySide6 desktop window. File scanning and detection features are intentionally added in later phases.
