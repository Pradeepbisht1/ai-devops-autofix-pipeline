import os

def test_app_file_exists():
    assert os.path.exists("app/src/app.py"), "app/src/app.py must exist"
