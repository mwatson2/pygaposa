from pygaposa.api import redactHeaders


def test_redact_headers_hides_sensitive_values():
    headers = {
        "Content-Type": "application/json",
        "authorization": "Bearer secret-token",
        "auth": '{"role": 1, "client": "abc"}',
    }
    redacted = redactHeaders(headers)

    assert redacted["Content-Type"] == "application/json"
    assert redacted["authorization"] == "**redacted**"
    assert redacted["auth"] == "**redacted**"
    assert "secret-token" not in str(redacted)


def test_redact_headers_does_not_mutate_original():
    headers = {"authorization": "Bearer secret-token"}
    redactHeaders(headers)
    assert headers["authorization"] == "Bearer secret-token"
