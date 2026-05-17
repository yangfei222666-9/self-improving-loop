from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPACE_DIR = ROOT / "demo" / "huggingface_space"


def test_huggingface_space_demo_files_exist():
    assert (SPACE_DIR / "app.py").exists()
    assert (SPACE_DIR / "requirements.txt").exists()


def test_huggingface_space_demo_is_bounded_and_package_backed():
    app = (SPACE_DIR / "app.py").read_text(encoding="utf-8")
    requirements = (SPACE_DIR / "requirements.txt").read_text(encoding="utf-8")

    assert "SelfImprovingLoop" in app
    assert "external_model_called" in app
    assert "simulated agent failure" in app
    assert "streamlit" in requirements
    assert "self-improving-loop" in requirements
