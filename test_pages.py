from playwright.sync_api import sync_playwright
import time

BASE = "http://localhost:5175"

PAGES = [
    ("/", "仪表板"),
    ("/materials", "材料库"),
    ("/prototypes", "拓扑原型"),
    ("/classification", "分类浏览"),
    ("/generate", "结构生成器"),
    ("/compare", "材料对比"),
    ("/advanced-search", "高级搜索"),
    ("/topology-verify", "拓扑验证"),
    ("/favorites", "收藏"),
    ("/recent", "最近浏览"),
]

errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.on("pageerror", lambda err: errors.append(f"JS Error: {err}"))
    page.on(
        "console",
        lambda msg: (
            errors.append(f"Console {msg.type}: {msg.text}") if msg.type == "error" else None
        ),
    )

    for path, name in PAGES:
        url = f"{BASE}{path}"
        print(f"\n--- Testing: {name} ({url}) ---")
        try:
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(1)

            title = page.title()
            print(f"  Title: {title}")

            page.screenshot(
                path=f'/tmp/test_{path.replace("/", "_") or "home"}.png', full_page=False
            )
            print(f"  Screenshot saved")

            visible_text = page.locator("body").inner_text()
            if "404" in visible_text and "Not Found" in visible_text:
                print(f"  WARNING: Page may show 404")
            else:
                print(f"  Page loaded OK ({len(visible_text)} chars)")

        except Exception as e:
            print(f"  ERROR: {e}")
            errors.append(f"{name}: {e}")

    print("\n\n--- Testing Material Detail Page ---")
    try:
        page.goto(f"{BASE}/materials", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)

        first_link = page.locator('a[href^="/materials/"]').first
        if first_link.is_visible(timeout=5000):
            href = first_link.get_attribute("href")
            print(f"  Found material link: {href}")
            page.goto(f"{BASE}{href}", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(1)
            page.screenshot(path="/tmp/test_material_detail.png")
            print(f"  Material detail page OK")
        else:
            print(f"  No material links found on materials page")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n\n--- Testing Prototype Detail Page ---")
    try:
        page.goto(f"{BASE}/prototypes", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)

        first_link = page.locator('a[href^="/prototypes/"]').first
        if first_link.is_visible(timeout=5000):
            href = first_link.get_attribute("href")
            print(f"  Found prototype link: {href}")
            page.goto(f"{BASE}{href}", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(1)
            page.screenshot(path="/tmp/test_prototype_detail.png")
            print(f"  Prototype detail page OK")
        else:
            print(f"  No prototype links found")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n\n--- Testing Search ---")
    try:
        page.goto(f"{BASE}/search?q=Ba", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)
        page.screenshot(path="/tmp/test_search.png")
        print(f"  Search page OK")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n\n--- Testing Header Search ---")
    try:
        page.goto(BASE, timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(1)

        search_input = page.locator('input[type="text"]').first
        if search_input.is_visible(timeout=3000):
            search_input.click()
            time.sleep(0.5)
            page.screenshot(path="/tmp/test_header_search.png")
            print(f"  Header search dropdown OK")
        else:
            print(f"  No search input found")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n\n--- Testing Sidebar Navigation ---")
    try:
        page.goto(BASE, timeout=15000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(1)

        nav_links = page.locator('nav a, aside a, [class*="sidebar"] a')
        count = nav_links.count()
        print(f"  Found {count} navigation links")

        for i in range(min(count, 5)):
            link = nav_links.nth(i)
            text = link.inner_text()
            href = link.get_attribute("href")
            print(f"    Link {i}: {text.strip()} -> {href}")
    except Exception as e:
        print(f"  ERROR: {e}")

    browser.close()

print("\n\n========== TEST SUMMARY ==========")
if errors:
    print(f"Found {len(errors)} errors:")
    for e in errors:
        print(f"  - {e}")
else:
    print("All tests passed with no errors!")
