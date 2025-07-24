import json
from ml_model import predict_failure

def test_prediction_output_format():
    test_input = {
        "build_time": 15,
        "error_count": 1,
        "cpu_usage": 75,
        "test_pass_rate": 0.9
    }
    result = predict_failure.predict_failure(test_input)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0
