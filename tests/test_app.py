import os

def test_app_file_exists():
    # ensure your app entrypoint is where you expect it
    assert os.path.exists("app/src/app.py"), "app/src/app.py must exist"
