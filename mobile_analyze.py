from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    iphone = p.devices['iPhone 14']
    context = browser.new_context(**iphone)
    page = context.new_page()

    issues = []

    def check_page(path, name):
        url = f'http://localhost:5176/CGCPT{path}'
        try:
            page.goto(url, timeout=15000)
            page.wait_for_load_state('networkidle', timeout=10000)
            page.wait_for_timeout(1500)
        except Exception as e:
            issues.append(f'[{name}] Load error: {e}')
            return

        viewport = page.viewport_size
        w = viewport['width']

        # Check horizontal overflow
        scroll_width = page.evaluate('document.documentElement.scrollWidth')
        client_width = page.evaluate('document.documentElement.clientWidth')
        if scroll_width > client_width + 5:
            issues.append(f'[{name}] HORIZONTAL OVERFLOW: scrollWidth={scroll_width} > clientWidth={client_width} (diff={scroll_width - client_width}px)')

        # Check for elements wider than viewport
        wide_elements = page.evaluate('''(vw) => {
            const results = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                if (rect.width > vw + 2 && rect.right > vw) {
                    const tag = el.tagName;
                    const cls = el.className ? el.className.toString().substring(0, 60) : '';
                    const id = el.id || '';
                    results.push(`${tag}#${id}.${cls} width=${Math.round(rect.width)}px right=${Math.round(rect.right)}px`);
                }
            }
            return results.slice(0, 10);
        }''', w)
        if wide_elements:
            for elem in wide_elements:
                issues.append(f'[{name}] WIDE ELEMENT: {elem}')

        # Check for tiny touch targets (buttons/links < 44px)
        small_targets = page.evaluate('''() => {
            const results = [];
            const interactives = document.querySelectorAll('button, a, input, select');
            for (const el of interactives) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && (rect.width < 36 || rect.height < 36)) {
                    const tag = el.tagName;
                    const text = (el.textContent || '').trim().substring(0, 20);
                    results.push(`${tag} "${text}" ${Math.round(rect.width)}x${Math.round(rect.height)}px`);
                }
            }
            return results.slice(0, 8);
        }''')
        if small_targets:
            for target in small_targets:
                issues.append(f'[{name}] SMALL TOUCH TARGET: {target}')

        # Check for text overflow / truncation issues
        truncated = page.evaluate('''() => {
            const results = [];
            const els = document.querySelectorAll('h1, h2, h3, p, span, td, th');
            for (const el of els) {
                if (el.scrollWidth > el.clientWidth + 5 && el.clientWidth > 0) {
                    const text = (el.textContent || '').trim().substring(0, 30);
                    results.push(`${el.tagName} "${text}" scrollW=${el.scrollWidth} clientW=${el.clientWidth}`);
                }
            }
            return results.slice(0, 5);
        }''')
        if truncated:
            for t in truncated:
                issues.append(f'[{name}] TEXT OVERFLOW: {t}')

        # Check console errors
        console_errors = []
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)

        # Check for overlapping elements (z-index issues)
        overlaps = page.evaluate('''() => {
            const results = [];
            const fixed = document.querySelectorAll('[class*="fixed"]');
            for (const el of fixed) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    const cls = el.className.toString().substring(0, 50);
                    results.push(`FIXED: ${el.tagName}.${cls} at ${Math.round(rect.left)},${Math.round(rect.top)} ${Math.round(rect.width)}x${Math.round(rect.height)}`);
                }
            }
            return results.slice(0, 5);
        }''')
        if overlaps:
            for o in overlaps:
                issues.append(f'[{name}] {o}')

        print(f'  [{name}] Checked (scrollW={scroll_width}, clientW={client_width})')

    pages = [
        ('/', 'Dashboard'),
        ('/materials', 'Materials'),
        ('/materials/mp-2998', 'MaterialDetail'),
        ('/prototypes', 'Prototypes'),
        ('/prototypes/pc-1', 'PrototypeDetail'),
        ('/compare', 'Compare'),
        ('/favorites', 'Favorites'),
        ('/recent', 'Recent'),
        ('/advanced-search', 'AdvancedSearch'),
        ('/search', 'Search'),
        ('/classify', 'Classify'),
        ('/verify', 'Verify'),
        ('/generate', 'Generate'),
    ]

    for path, name in pages:
        check_page(path, name)

    context.close()
    browser.close()

    print('\n' + '='*60)
    print('MOBILE ISSUES FOUND:')
    print('='*60)
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f'{i}. {issue}')
    else:
        print('No issues found!')
    print(f'\nTotal issues: {len(issues)}')
