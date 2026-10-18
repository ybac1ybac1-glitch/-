from pathlib import Path

def test_windows_acceptance_cmd_is_ascii_and_has_safe_paths():
    path=Path(__file__).parents[1]/"backend"/"windows_acceptance.cmd"
    raw=path.read_bytes()
    raw.decode("ascii")
    text=raw.decode("ascii")
    assert 'cd /d "%~dp0"' in text
    assert 'start "Strategy A Flask" /D "%~dp0"' in text
    assert "%ERRORLEVEL%" in text
    assert "mode=ro" not in text
