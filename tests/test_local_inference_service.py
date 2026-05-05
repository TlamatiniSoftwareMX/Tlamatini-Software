from core.local_inference_service import _normalizar_n_predict


def test_normalizar_n_predict_evita_cero_tokens():
    assert _normalizar_n_predict(0) == 512
    assert _normalizar_n_predict("0") == 512
    assert _normalizar_n_predict(-1) == 512
    assert _normalizar_n_predict(None) == 512


def test_normalizar_n_predict_respeta_valores_validos():
    assert _normalizar_n_predict(1) == 1
    assert _normalizar_n_predict(256) == 256
