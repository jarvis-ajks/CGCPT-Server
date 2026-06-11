from playwright.sync_api import sync_playwright
import time

BASE = "http://localhost:5175"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.on("pageerror", lambda err: print(f"JS ERROR: {err}"))
    page.on(
        "console",
        lambda msg: (
            print(f"CONSOLE {msg.type}: {msg.text[:200]}")
            if msg.type in ("error", "warning")
            else None
        ),
    )

    print("=== 1. Dashboard API Data ===")
    page.goto(BASE, timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(3)
    page.screenshot(path="/tmp/check_dashboard.png")

    stats_cards = page.locator('[class*="rounded"]')
    print(f"  Cards found: {stats_cards.count()}")

    print("\n=== 2. Materials Browser ===")
    page.goto(f"{BASE}/materials", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(3)
    page.screenshot(path="/tmp/check_materials.png")

    rows = page.locator('table tbody tr, [class*="card"]')
    print(f"  Table rows/cards: {rows.count()}")

    search_input = page.locator('input[placeholder*="搜索"], input[placeholder*="化学式"]').first
    if search_input.is_visible(timeout=3000):
        search_input.fill("Ba")
        page.wait_for_timeout(1000)
        page.screenshot(path="/tmp/check_materials_search.png")
        print(f"  Search test OK")
    else:
        print(f"  No search input found")

    print("\n=== 3. Classification Browser ===")
    page.goto(f"{BASE}/classify", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(3)
    page.screenshot(path="/tmp/check_classify.png")

    topology_btn = page.locator('button:has-text("拓扑"), button:has-text("topology")').first
    if topology_btn.is_visible(timeout=3000):
        print(f"  Topology tab found")
    else:
        print(f"  No topology tab found")

    print("\n=== 4. Topology Verify ===")
    page.goto(f"{BASE}/verify", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    page.screenshot(path="/tmp/check_verify.png")

    load_btn = page.locator('button:has-text("加载")').first
    if load_btn.is_visible(timeout=3000):
        print(f"  Load data button found")
    else:
        print(f"  No load button found")

    print("\n=== 5. Advanced Search ===")
    page.goto(f"{BASE}/advanced-search", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    page.screenshot(path="/tmp/check_advanced_search.png")

    search_btn = page.locator('button:has-text("搜索")').first
    if search_btn.is_visible(timeout=3000):
        search_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="/tmp/check_advanced_search_results.png")
        print(f"  Search executed OK")
    else:
        print(f"  No search button found")

    print("\n=== 6. Compare Page ===")
    page.goto(f"{BASE}/compare", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    page.screenshot(path="/tmp/check_compare.png")

    search_compare = page.locator('input[placeholder*="搜索"], input[placeholder*="化学式"]').first
    if search_compare.is_visible(timeout=3000):
        search_compare.fill("Ba")
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        page.screenshot(path="/tmp/check_compare_search.png")
        print(f"  Compare search OK")
    else:
        print(f"  No search input in compare")

    print("\n=== 7. Structure Generator ===")
    page.goto(f"{BASE}/generate", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    page.screenshot(path="/tmp/check_generator.png")

    gen_btn = page.locator('button:has-text("生成结构")').first
    if gen_btn.is_visible(timeout=3000):
        print(f"  Generate button found")
    else:
        print(f"  No generate button found")

    print("\n=== 8. Favorites (empty) ===")
    page.goto(f"{BASE}/favorites", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(1)
    page.screenshot(path="/tmp/check_favorites.png")
    print(f"  Favorites page loaded")

    print("\n=== 9. Recent (empty) ===")
    page.goto(f"{BASE}/recent", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(1)
    page.screenshot(path="/tmp/check_recent.png")
    print(f"  Recent page loaded")

    print("\n=== 10. Material Detail + Favorite ===")
    page.goto(f"{BASE}/materials", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)

    first_link = page.locator('a[href^="/materials/"]').first
    if first_link.is_visible(timeout=5000):
        href = first_link.get_attribute("href")
        page.goto(f"{BASE}{href}", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)
        page.screenshot(path="/tmp/check_material_detail.png")

        fav_btn = page.locator('button:has-text("收藏"), button:has(svg.heart)').first
        if fav_btn.is_visible(timeout=3000):
            fav_btn.click()
            page.wait_for_timeout(500)
            print(f"  Favorite button clicked")
        else:
            print(f"  No favorite button found")

        page.goto(f"{BASE}/favorites", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(1)
        page.screenshot(path="/tmp/check_favorites_after.png")
        print(f"  Favorites page after adding")

    print("\nAll checks completed!")
    browser.close()
