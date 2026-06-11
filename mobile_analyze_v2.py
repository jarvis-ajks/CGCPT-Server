from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    iphone = p.devices["iPhone 14"]
    context = browser.new_context(**iphone)
    page = context.new_page()

    issues = []

    def check_page(path, name):
        url = f"http://118.31.164.41/CGCPT{path}"
        try:
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            page.wait_for_timeout(2000)
        except Exception as e:
            issues.append(f"[{name}] Load error: {e}")
            return

        w = page.viewport_size["width"]

        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        client_width = page.evaluate("document.documentElement.clientWidth")
        if scroll_width > client_width + 5:
            issues.append(f"[{name}] HORIZONTAL OVERFLOW: {scroll_width - client_width}px")

        wide_elements = page.evaluate(
            """(vw) => {
            const results = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                if (rect.width > vw + 2 && rect.right > vw) {
                    results.push(`${el.tagName} width=${Math.round(rect.width)}`);
                }
            }
            return results.slice(0, 5);
        }""",
            w,
        )
        if wide_elements:
            for elem in wide_elements:
                issues.append(f"[{name}] WIDE: {elem}")

        small_targets = page.evaluate(
            """() => {
            const results = [];
            const interactives = document.querySelectorAll('button, a, input, select');
            for (const el of interactives) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && (rect.width < 32 || rect.height < 32)) {
                    results.push(`${el.tagName} ${Math.round(rect.width)}x${Math.round(rect.height)}`);
                }
            }
            return results.length;
        }"""
        )
        if small_targets > 0:
            issues.append(f"[{name}] SMALL TOUCH TARGETS: {small_targets}")

        print(
            f"  [{name}] scrollW={scroll_width} clientW={client_width} small_targets={small_targets}"
        )

    pages = [
        ("/", "Dashboard"),
        ("/materials", "Materials"),
        ("/materials/mp-2998", "MaterialDetail"),
        ("/prototypes", "Prototypes"),
        ("/prototypes/pc-1", "PrototypeDetail"),
        ("/compare", "Compare"),
        ("/favorites", "Favorites"),
        ("/recent", "Recent"),
        ("/advanced-search", "AdvancedSearch"),
        ("/search", "Search"),
        ("/classify", "Classify"),
        ("/verify", "Verify"),
        ("/generate", "Generate"),
    ]

    for path, name in pages:
        check_page(path, name)

    context.close()
    browser.close()

    print("\n" + "=" * 60)
    print("REMAINING MOBILE ISSUES:")
    print("=" * 60)
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    else:
        print("No issues found!")
    print(f"\nTotal issues: {len(issues)}")
