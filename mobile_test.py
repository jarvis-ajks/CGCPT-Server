from playwright.sync_api import sync_playwright

PAGES = [
    ('/', 'Dashboard'),
    ('/materials', 'Materials'),
    ('/advanced-search', 'AdvancedSearch'),
    ('/verify', 'Verify'),
    ('/generate', 'Generate'),
    ('/prototypes', 'Prototypes'),
    ('/recent', 'Recent'),
]

BASE = 'http://118.31.164.41/CGCPT'
VIEWPORT = {'width': 390, 'height': 844}

def check_page(page, path, name):
    issues = []
    try:
        page.goto(f'{BASE}{path}', timeout=30000)
        page.wait_for_load_state('networkidle', timeout=15000)
    except Exception as e:
        return [{'type': 'load_error', 'detail': str(e)[:100]}]

    body = page.locator('body')
    body_width = body.bounding_box()
    vw = VIEWPORT['width']

    wide_elements = page.evaluate(f"""() => {{
        const vw = {vw};
        const results = [];
        const all = document.querySelectorAll('*');
        for (const el of all) {{
            const rect = el.getBoundingClientRect();
            if (rect.width > vw + 2 && rect.width < 2000) {{
                const tag = el.tagName.toLowerCase();
                const cls = el.className ? String(el.className).substring(0, 60) : '';
                results.push({{ tag, cls, width: Math.round(rect.width) }});
            }}
        }}
        return results.slice(0, 10);
    }}""")

    for w in wide_elements:
        issues.append({'type': 'wide_element', 'tag': w['tag'], 'width': w['width'], 'cls': w['cls']})

    small_touch = page.evaluate(f"""() => {{
        const vw = {vw};
        const results = [];
        const interactives = document.querySelectorAll('button, a, [role="button"], input[type="checkbox"]');
        for (const el of interactives) {{
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                if (rect.height < 36 || rect.width < 36) {{
                    const tag = el.tagName.toLowerCase();
                    const text = (el.textContent || '').trim().substring(0, 20);
                    const cls = el.className ? String(el.className).substring(0, 50) : '';
                    results.push({{ tag, text, cls, w: Math.round(rect.width), h: Math.round(rect.height) }});
                }}
            }}
        }}
        return results;
    }}""")

    for s in small_touch:
        issues.append({'type': 'small_touch', 'tag': s['tag'], 'text': s['text'], 'w': s['w'], 'h': s['h'], 'cls': s['cls']})

    return issues

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport=VIEWPORT,
        device_scale_factor=3,
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
    )
    page = context.new_page()

    total_wide = 0
    total_small = 0

    for path, name in PAGES:
        issues = check_page(page, path, name)
        wide = [i for i in issues if i['type'] == 'wide_element']
        small = [i for i in issues if i['type'] == 'small_touch']
        total_wide += len(wide)
        total_small += len(small)

        print(f'\n=== {name} ({path}) ===')
        if wide:
            print(f'  Wide elements ({len(wide)}):')
            for w in wide:
                print(f'    <{w["tag"]}> width={w["width"]}px class="{w["cls"]}"')
        if small:
            print(f'  Small touch targets ({len(small)}):')
            for s in small[:15]:
                print(f'    <{s["tag"]}> {s["w"]}x{s["h"]} text="{s["text"]}" cls="{s["cls"]}"')
            if len(small) > 15:
                print(f'    ... and {len(small) - 15} more')
        if not wide and not small:
            print('  ✅ No issues!')

    print(f'\n=== SUMMARY ===')
    print(f'Total wide elements: {total_wide}')
    print(f'Total small touch targets: {total_small}')
    print(f'Total issues: {total_wide + total_small}')

    browser.close()
