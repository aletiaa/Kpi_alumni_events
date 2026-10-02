from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desktop_navigation_breakpoint():
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert "@media (max-width: 1199px)" in css
    assert "@media (min-width: 1200px) and (max-width: 1500px)" in css
    assert "@media (max-width: 1500px) { .topbar" not in css


def test_responsive_hero_assets_and_preloads():
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    home = (ROOT / "app/templates/home.html").read_text(encoding="utf-8")
    original = ROOT / "app/static/img/kpi-main.png"
    for name, limit in (("kpi-main.webp", 200_000), ("kpi-main-mobile.webp", 80_000)):
        image = ROOT / "app/static/img" / name
        assert image.stat().st_size < min(original.stat().st_size, limit)
        assert image.read_bytes()[:4] == b"RIFF"
        assert name in css
        assert name in home
    assert 'media="(max-width: 720px)"' in home
    assert 'media="(min-width: 721px)"' in home
