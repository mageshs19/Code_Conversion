$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:STREAMLIT_SERVER_FILE_WATCHER_TYPE = "none"
$env:STREAMLIT_SERVER_HEADLESS = "true"
$env:PYTHONPATH = "src;."
python -m streamlit run src\idms_db2_phase2\app.py