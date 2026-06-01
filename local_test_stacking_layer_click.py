from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    cif_path = Path(__file__).resolve().parent / "test_cifs" / "test_XO3_M7_XO3_M7_XO3_XO3_1.cif"

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto("http://127.0.0.1:4173/CGCPT/stacking", wait_until="networkidle")
        page.locator('input[type="file"]').set_input_files(str(cif_path))
        page.wait_for_timeout(1200)

        page.get_by_role("button", name="第 1 层").click()
        page.wait_for_timeout(300)

        if errors:
            raise SystemExit("PAGEERROR: " + " | ".join(errors[:3]))

        browser.close()


if __name__ == "__main__":
    main()
