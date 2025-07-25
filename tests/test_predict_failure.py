from ml_model.predict_failure import predict_failure

def test_prediction_output_format():
    metrics = {
        "build_time": 15,
        "error_count": 1,
        "cpu_usage": 75,
        "test_pass_rate": 0.9,
    }
    prob = predict_failure(metrics)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0
