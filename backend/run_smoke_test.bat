@echo off
REM Quick smoke-test ingestion: just Base Set Charizard.
call venv\Scripts\activate.bat
python cli.py --smoke-test
