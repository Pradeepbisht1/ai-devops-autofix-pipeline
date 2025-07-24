import subprocess
import sys
from unittest import mock
import pipeline.scripts.smart_auto_heal as auto_heal

@mock.patch("subprocess.run")
def test_auto_heal_kubectl_trigger(mock_run):
    mock_run.return_value = mock.Mock(returncode=0)
    sys.argv = [
        "smart_auto_heal.py",
        "--deployment", "my-app",
        "--namespace", "prod",
        "--replicas", "2"
    ]
    try:
        auto_heal.main()
    except SystemExit:
        pass
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "kubectl" in cmd[0]
