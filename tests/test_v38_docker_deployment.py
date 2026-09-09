from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]


def test_docker_runtime_contract():
    text = (ROOT / "Dockerfile").read_text()
    assert "python:3.11-slim" in text
    assert "USER alimj" in text
    assert 'CMD ["python", "-m", "bot.main"]' in text
    assert "/health" in text
    assert "HEALTHCHECK" in text


def test_compose_hardening_contract():
    text = (ROOT / "docker-compose.yml").read_text()
    assert "restart: unless-stopped" in text
    assert "init: true" in text
    assert "no-new-privileges:true" in text
    assert "stop_grace_period: 30s" in text
    assert "8080:8080" in text


def test_dockerignore_protects_local_and_immutable_content():
    text = (ROOT / ".dockerignore").read_text()
    for item in [".env", "tests", "__pycache__", "bot/features/fun/jokes_data.json"]:
        assert item in text


def test_release_is_38():
    assert 'VERSION = "58.0.0"' in (ROOT / "bot/release.py").read_text()
    assert 'RELEASE_VERSION\n        value: "58.0.0"' in (ROOT / "render.yaml").read_text()


def test_requirements_and_jokes_are_untouched():
    req = (ROOT / "requirements.txt").read_bytes()
    assert b"python-telegram-bot[job-queue]==20.3" in req
    jokes = ROOT / "bot/features/fun/jokes_data.json"
    if jokes.exists():
        assert hashlib.sha256(jokes.read_bytes()).hexdigest() == "dc573e2a954af897350caa4183a98f33d5ed71327fed02c7ebe053d893e3a508"
