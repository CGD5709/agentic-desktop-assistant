"""
Unit tests for the voice_cleaner text sanitization module.
"""
from agent.voice_cleaner import clean_text_for_speech


def test_clean_markdown_formatting():
    raw = "Hola **Jose**, he analizado el *sistema* y todo está en orden."
    cleaned = clean_text_for_speech(raw)
    assert "**" not in cleaned
    assert "*" not in cleaned
    assert "Hola Jose, he analizado el sistema y todo está en orden." in cleaned


def test_clean_code_blocks():
    raw = "Aquí tienes el script:\n```python\nprint('hello')\n```\n¿Deseas ejecutarlo?"
    cleaned = clean_text_for_speech(raw)
    assert "print('hello')" not in cleaned
    assert "código correspondiente en pantalla" in cleaned
    assert "¿Deseas ejecutarlo?" in cleaned


def test_clean_tables():
    raw = "Resultados del diagnóstico:\n| Proceso | PID | RAM |\n| notepad | 123 | 50MB |\n| chrome | 456 | 400MB |\nTodo correcto."
    cleaned = clean_text_for_speech(raw)
    assert "|" not in cleaned
    assert "tabla en pantalla" in cleaned
    assert "Todo correcto." in cleaned


def test_clean_emojis_and_headers():
    raw = "### Diagnóstico Completado 🚀\n- CPU: 12% 📊\n- RAM: 45%"
    cleaned = clean_text_for_speech(raw)
    assert "###" not in cleaned
    assert "🚀" not in cleaned
    assert "📊" not in cleaned
    assert "Diagnóstico Completado" in cleaned
