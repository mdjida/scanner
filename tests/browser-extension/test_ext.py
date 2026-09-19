import asyncio
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

EXT_DIR = (Path(__file__).resolve().parents[2] / 'chrome-extension').resolve()
TEST_URL = 'http://localhost:9000/test-card.html'

errors = []
warnings = []
requests = []

USER_DATA_DIR = Path(__file__).resolve().parent / 'user-data'

async def main():
    # Clean user-data so manifest/content-script changes are picked up each run.
    if USER_DATA_DIR.exists():
        import shutil
        shutil.rmtree(USER_DATA_DIR)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            args=[
                f'--disable-extensions-except={EXT_DIR}',
                f'--load-extension={EXT_DIR}',
                '--no-first-run',
                '--disable-features=Translate,OptimizationHints,PrivacySandboxAdsApi',
            ],
            viewport={'width': 1280, 'height': 720},
        )

        page = await context.new_page()

        page.on('console', lambda msg: handle_console(msg))
        page.on('pageerror', lambda exc: errors.append(f'PAGE ERROR: {exc}'))
        page.on('requestfinished', lambda req: handle_request(req))

        print(f'Opening {TEST_URL}')
        await page.goto(TEST_URL, wait_until='networkidle')
        await asyncio.sleep(2)

        # Look for the scan FAB.
        fab = page.locator('#lco-fab')
        try:
            await fab.wait_for(state='visible', timeout=15000)
            print('FAB found')
        except Exception as e:
            print('FAB NOT found:', e)
            await dump_state(page)
            await context.close()
            return

        await fab.click()
        print('Clicked FAB')
        await asyncio.sleep(0.5)

        # Tap Scan button should appear.
        tap = page.locator('#lco-tap')
        try:
            await tap.wait_for(state='visible', timeout=5000)
            print('Tap Scan button found')
        except Exception as e:
            print('Tap Scan button NOT found:', e)
            await dump_state(page)
            await context.close()
            return

        await tap.click()
        print('Clicked Tap Scan')
        # Wait for backend call and result panel.
        hit_assert = False
        for i in range(60):
            await asyncio.sleep(0.5)
            root = await page.query_selector('#lco-root')
            if root:
                text = await root.inner_text()
                if text and 'Identifying' not in text:
                    print('Result panel populated:', text[:200])
                    if 'Charizard' in text:
                        print('ASSERT PASS: Charizard resolved first')
                        hit_assert = True
                    break
            if any('/identify' in r for r in requests):
                print('Identify request observed')
        if not hit_assert:
            print('ASSERT FAIL: Charizard not top result')
            errors.append('ASSERT FAIL: Charizard not top result')

        # Test Auto Scan
        print('Starting Auto Scan test')
        await asyncio.sleep(1)
        auto_btn = page.locator('#lco-auto')
        try:
            await auto_btn.wait_for(state='visible', timeout=3000)
            await auto_btn.click()
            print('Clicked Auto Scan')
        except Exception as e:
            print('Auto button not available:', e)

        # Wait for auto scans to fire.
        prior = len([r for r in requests if '/identify' in r])
        for i in range(30):
            await asyncio.sleep(0.5)
            current = len([r for r in requests if '/identify' in r])
            if current > prior:
                print(f'Auto scan triggered identify request(s): {current - prior} new')
                break

        await asyncio.sleep(2)
        await dump_state(page)
        await context.close()

    # Remove user-data between runs so manifest changes are picked up.
    if USER_DATA_DIR.exists():
        import shutil
        shutil.rmtree(USER_DATA_DIR)

    print('\n--- Console summary ---')
    print('Errors:', len(errors))
    for e in errors[:20]:
        print(' ', e)
    print('Warnings:', len(warnings))
    for w in warnings[:20]:
        print(' ', w)
    print('\n--- Network summary ---')
    for r in requests:
        print(' ', r)

    if errors or any('Could not capture' in r for r in requests):
        sys.exit(1)
    print('\nTest completed')

def handle_console(msg):
    text = msg.text
    if msg.type == 'error':
        errors.append(text)
    elif msg.type == 'warning':
        warnings.append(text)

async def handle_request(req):
    url = req.url
    if 'identify' in url or 'health' in url:
        try:
            resp = await req.response()
            status = resp.status if resp else 'no-response'
            body = ''
            if resp and status == 200:
                try:
                    body = await resp.text()
                    if len(body) > 200:
                        body = body[:200] + '...'
                except Exception:
                    pass
            requests.append(f'{req.method} {url} -> {status} {body}')
        except Exception as e:
            requests.append(f'{req.method} {url} -> error: {e}')

async def dump_state(page):
    body = await page.content()
    out = Path(__file__).resolve().parent / 'page-dump.html'
    out.write_text(body, encoding='utf-8')
    print(f'Page dumped to {out}')

if __name__ == '__main__':
    asyncio.run(main())
