import re, shutil, subprocess, tempfile
from pathlib import Path

def test_strategy_a_v4_template_javascript_parses():
    text=Path(__file__).parents[1].joinpath("backend","templates","strategy_a_v4.html").read_text(encoding="utf-8")
    script=re.search(r"<script>(.*?)</script>",text,re.S).group(1)
    assert "\\n" not in script
    node=shutil.which("node")
    if not node:
        return
    with tempfile.NamedTemporaryFile("w",suffix=".js",encoding="utf-8",delete=False) as f:
        f.write(script); path=f.name
    try:
        result=subprocess.run([node,"--check",path],capture_output=True,text=True)
        assert result.returncode==0, result.stderr
    finally:
        Path(path).unlink(missing_ok=True)
