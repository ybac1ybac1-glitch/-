from pathlib import Path

def test_autostart_scripts_are_ascii_and_single_instance_safe():
    root=Path(__file__).parents[1]/"backend"
    for name in ("install_autostart.cmd","uninstall_autostart.cmd","status_autostart.cmd","windows_autostart_install.ps1","windows_autostart_uninstall.ps1","windows_autostart_status.ps1"):
        text=(root/name).read_bytes().decode("ascii")
        assert text.strip()
    install=(root/"windows_autostart_install.ps1").read_text()
    assert "AStockStrategyA-V4" in install
    assert "MultipleInstances IgnoreNew" in install
    assert "Read-Host" in install
