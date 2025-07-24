import subprocess
import sys
from unittest import mock
import pipeline.scripts.smart_auto_heal as auto_heal

@mock.patch("subprocess.run")
def test_auto_heal_kubectl_trigger(mock_run):
    # simulate kubectl command success
    mock_run.return_value = mock.Mock(returncode=0)
    # emulate CLI args for auto-heal
    sys.argv = [
        "smart_auto_heal.py",
        "--deployment", "my-app",
        "--namespace", "prod",
        "--replicas", "2"
    ]
    # calling main should invoke subprocess.run
    try:
        auto_heal.main()
    except SystemExit:
        pass  # ignore exit
    # ensure kubectl was called at least once
    assert mock_run.called
    # we can check the first call was kubectl set
    cmd = mock_run.call_args[0][0]
    assert "kubectl" in cmd[0]
