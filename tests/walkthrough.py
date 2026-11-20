import asyncio, os
from playwright.async_api import async_playwright

import pathlib
HTML = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').read_text()
SHOTS = str(pathlib.Path(__file__).resolve().parent / 'shots'); os.makedirs(SHOTS, exist_ok=True)
# Viewer emulation: sandboxed cross-origin frame, and the parent rewrites the frame's hash back
# whenever it changes (the behaviour that broke v1).
OUTER = '<iframe id=f sandbox="allow-scripts allow-forms" style="width:1440px;height:1000px;border:0"></iframe>'
log = []
def step(role, msg, ok=True):
    log.append(f"{'PASS' if ok else 'FAIL'} [{role}] {msg}")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg = await b.new_page(viewport={'width': 1440, 'height': 1000})
        errs = []
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.set_content(OUTER)
        await pg.evaluate("h=>document.getElementById('f').srcdoc=h", HTML)
        await pg.wait_for_timeout(1500)
        f = pg.frames[1]
        f.on = None
        await f.evaluate("window.addEventListener('hashchange',()=>{history.replaceState(null,'',' ')})")
        txt = lambda: f.evaluate("document.body.innerText")
        n = [0]
        async def shot(name):
            n[0] += 1
            await pg.screenshot(path=f'{SHOTS}/{n[0]:02d}-{name}.png', full_page=False)
        async def has(s): return s.lower() in (await txt()).lower()

        # ---------- Visitor ----------
        R = 'Visitor'
        step(R, 'Public portal loads', await has('One national ledger'))
        await f.fill('input[data-in=q]', 'peat')
        rows = await f.evaluate("document.querySelectorAll('#projRows tr').length")
        step(R, f'Keyword "peat" filters project list to {rows} row(s)', rows == 1)
        await f.fill('input[data-in=q]', '')
        await f.select_option('select[data-in=state]', 'Sabah')
        rows = await f.evaluate("document.querySelectorAll('#projRows tr').length")
        step(R, f'State = Sabah filters to {rows} row(s)', rows == 1)
        await f.click('button:has-text("Reset")')
        await shot('visitor-public')
        await f.click('.pubnav >> text=Sign in')
        step(R, 'Sign in opens the login page', await has('Sign in to your registry account'))

        # ---------- Registry Administrator ----------
        R = 'Admin'
        await f.click('button:has-text("Registry Administrator (NRES)")')
        await f.click('form >> button.btn:has-text("Sign in")')
        step(R, 'Signs in to the dashboard', await has('Approval queue'))
        q = await f.evaluate("document.querySelectorAll('.main table')[0].querySelectorAll('tbody tr').length")
        step(R, f'Approval queue shows {q} items', q >= 4)
        await shot('admin-dashboard')
        await f.click('tr:has-text("ACC-0151") >> text=Review')
        step(R, 'Queue "Review" opens Accounts & KYC', await has('KYC review · ACC-0151'))
        await f.click('button:has-text("Approve & activate account")')
        step(R, 'Approves KYC → account Active', await has('Decision recorded: Active'))
        await f.click('.side >> text=Project Registration')
        await f.click('button:has-text("Approve registration")')
        step(R, 'Approves Kemena Mangrove project → Registered', await has('Registered. The project now appears'))
        await f.click('tr:has-text("NCR-PRJ-SBH-0029")')
        await f.click('button:has-text("Advance to next stage")')
        step(R, 'Opens Kinabatangan project and advances it to Validation', await has('NCR-PRJ-SBH-0029 · Kinabatangan') and 'Validation' in await f.inner_text('.steps .cur'))
        await shot('admin-project')
        await f.click('.side >> text=CCU Issuance')
        await f.click('button:has-text("Approve & issue")')
        step(R, 'Approval without OTP is refused', await has('Enter a 6-digit one-time password'))
        await f.fill('#otp', '123456')
        await f.click('button:has-text("Approve & issue")')
        step(R, 'Issues 100,000 CCU with serials and buffer', await has('Issued 100,000 CCU'))
        await f.click('tr:has-text("ISS-2026-0121")')
        await f.click('button:has-text("Simulate fee payment")')
        await f.fill('#otp', '654321')
        await f.click('button:has-text("Approve & issue")')
        step(R, 'Second request: fee paid, then issued 48,200', await has('Issued 48,200 CCU'))
        await shot('admin-issuance')
        await f.click('.side >> text=Transfers & Article 6')
        await f.fill('#authQty', '40000')
        await f.click('button:has-text("Authorise & transfer")')
        step(R, 'Authorises 40,000 ITMOs → CA ledger entry', await has('Letter of authorisation issued') and await has('40,000'))
        await f.click('button:has-text("Simulate Verra lock confirmation")')
        step(R, 'Confirms Verra lock for VCS import', not await has("Waiting for Verra"))
        await shot('admin-transfers')
        await f.click('.side >> text=Reporting, Validity & Policy')
        await f.fill('#pIntl', '20')
        await f.click('button:has-text("Save as new version")')
        step(R, 'Sets international threshold to 20% (policy v2)', await has('international 50→20%'))
        await f.click('tr:has-text("ACC-0098") >> button:has-text("Send reminder")')
        step(R, 'Sends expiry reminder', await has('Reminder sent to ACC-0098'))
        await shot('admin-policy')
        await f.click('.side >> text=Public registry view')
        step(R, 'Public portal reflects issuance and ITMOs', await has('4,960,760') and await has('40,000'))
        await f.click('text=Back to my console')
        step(R, 'Returns to the console; queue now shorter', await has('Approval queue'))

        # ---------- Account holder ----------
        R = 'Account holder'
        await f.click('button:has-text("Switch role")')
        step(R, 'Switches to Sample Cement Bhd portal (menu shows holder modules only)', await has('My holding') and 'CCU Issuance' not in await f.inner_text('.side'))
        await f.click('tr:has-text("L-2198")')
        await f.fill('input[data-in=tradeQty]', '50')
        step(R, 'Quantity below 100 disables payment', await f.is_disabled('#payBtn'))
        await f.fill('input[data-in=tradeQty]', '2000')
        step(R, 'Total and line recalculate live (2,000 × RM 38.50 + fee)', (await f.inner_text('#tTot')) == 'RM 77,200.00' and (await f.inner_text('#tLine')).startswith('2,000'))
        await f.check('input[data-m="DuitNow"]')
        await f.click('#payBtn')
        step(R, 'Payment dialog opens', await has('DuitNow · simulated'))
        await shot('holder-payment')
        await f.click('button:has-text("Approve payment")')
        step(R, 'Payment confirmed, 2,000 VCS units delivered to holding', await has('MY-VCS-PHG-0007-2024-002-0000001–0002000'))
        await shot('holder-trading')
        await f.click('.side >> text=Carbon Levy Offset')
        await f.click('button:has-text("Example: too many international")')
        step(R, 'Too many international credits → blocked with guidance', await has('Too many international credits') and await f.is_disabled('button:has-text("Surrender")'))
        await shot('holder-levy-blocked')
        await f.click('button:has-text("Example: valid mix")')
        blocked = await has('Too many international credits')
        step(R, 'Preset 5,000 domestic + 3,000 international fails under the new 20% threshold', blocked)
        inputs = await f.query_selector_all('input[data-in=levyQty]')
        # set international inputs to 1,000 total
        for el in inputs:
            idv = await el.get_attribute('data-id')
            intl = await f.evaluate(f"S.blocks.find(b=>b.id==='{idv}').intl")
            if intl:
                await el.fill('')
        first_intl = None
        for el in inputs:
            idv = await el.get_attribute('data-id')
            if await f.evaluate(f"S.blocks.find(b=>b.id==='{idv}').intl"):
                first_intl = el; break
        await first_intl.fill('1000')
        step(R, 'Reduces international to 1,000 → both checks pass', not await has('Too many international credits') and not await f.is_disabled('button:has-text("Surrender")'))
        await f.click('button:has-text("Surrender")')
        step(R, 'Surrenders 6,000 CCU against the levy', await has('of which international 1,000') and await has('11,000'))
        await shot('holder-levy-done')
        await f.click('.side >> text=CCU Retirement')
        await f.fill('input[data-in=retQty]', '500')
        await f.fill('input[data-in=retBen]', 'Sample Cement Bhd – Kanthan plant')
        await f.click('#retBtn')
        step(R, 'Retires 500 CCU and receives certificate', await has('Certificate of Retirement') and await has('Kanthan plant'))
        await shot('holder-certificate')
        await f.click('.side >> text=Public registry view')
        step(R, 'Retirement visible on the public registry', await has('Sample Cement Bhd – Kanthan plant'))
        await f.click('text=Back to my console')
        await f.click('button:has-text("Sign out")')
        step('Visitor', 'Sign out returns to the public portal', await has('One national ledger'))

        step('All', f'No script errors ({len(errs)})', not errs)
        for e in errs: log.append('  error: ' + e)
        await b.close()
    print('\n'.join(log))

asyncio.run(main())
