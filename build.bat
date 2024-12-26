@echo off
python -m venv env
start .\env\scripts\activate.bat
pip install pyqt6 frenpy pyinstaller
python .\env\Lib\site-packages\PyInstaller main.py --onefile