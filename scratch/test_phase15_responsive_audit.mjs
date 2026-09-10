// scratch/test_phase15_responsive_audit.mjs
import { spawn } from 'child_process';

const CHROME_BIN = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9268;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitForChromeTarget(port, maxTries = 30) {
  for (let i = 0; i < maxTries; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/new`, { method: 'PUT' });
      const target = await res.json();
      if (target && target.webSocketDebuggerUrl) return target;
    } catch (e) {
      await sleep(300);
    }
  }
  throw new Error(`Chrome debugging port ${port} not ready`);
}

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 1;
    this.callbacks = new Map();
  }
  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
  }
  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = this.id++;
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() {
    if (this.ws) this.ws.close();
  }
}

const VIEWPORTS = [
  { name: "iPhone 12/13/14 (Mobile)", width: 390, height: 844, deviceScaleFactor: 3, mobile: true },
  { name: "iPhone 14/15 Pro (Mobile)", width: 393, height: 852, deviceScaleFactor: 3, mobile: true },
  { name: "Pixel 7 / Galaxy S (Mobile)", width: 412, height: 915, deviceScaleFactor: 2.625, mobile: true },
  { name: "iPad Mini / Portrait (Tablet)", width: 768, height: 1024, deviceScaleFactor: 2, mobile: true },
  { name: "Laptop Small (Desktop)", width: 1366, height: 768, deviceScaleFactor: 1, mobile: false },
  { name: "MacBook Pro 14 (Desktop)", width: 1440, height: 900, deviceScaleFactor: 2, mobile: false },
  { name: "Full HD (Desktop)", width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false }
];

async function runResponsiveAudit() {
  console.log("======================================================================");
  console.log("PHASE 15: RESPONSIVE & MULTI-VIEWPORT AUDIT MATRIX");
  console.log("======================================================================");

  const chromeProc = spawn(CHROME_BIN, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--no-sandbox',
    '--disable-gpu',
    '--user-data-dir=/tmp/chrome-phase15-audit'
  ]);

  try {
    const target = await waitForChromeTarget(PORT);
    const client = new CDPClient(target.webSocketDebuggerUrl);
    await client.connect();

    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('DOM.enable');

    // First load to authenticate or skip intro
    await client.send('Page.navigate', { url: 'http://localhost:3000' });
    await sleep(2000);

    // Skip intro to authenticate
    await client.send('Runtime.evaluate', {
      expression: `
        sessionStorage.setItem('bharat_intro_completed', 'true');
        location.reload();
      `
    });
    await sleep(2500);

    // Register a test customer to unlock the complete storefront
    const ts = Date.now();
    const testEmail = `resp_test_${ts}@example.com`;
    const testPhone = `98${Math.floor(10000000 + Math.random() * 90000000)}`;
    await client.send('Runtime.evaluate', {
      expression: `
        (async () => {
          const tabBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Create Account'));
          if (tabBtn) tabBtn.click();
        })()
      `
    });
    await sleep(600);

    await client.send('Runtime.evaluate', {
      expression: `
        (() => {
          const inputs = Array.from(document.querySelectorAll('input'));
          const nameInput = inputs.find(i => i.name === 'full_name');
          const emailInput = inputs.find(i => i.name === 'email');
          const phoneInput = inputs.find(i => i.name === 'phone_number');
          const passInput = inputs.find(i => i.name === 'password');
          
          const setVal = (input, val) => {
            if (!input) return;
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, val);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
          };

          setVal(nameInput, "Resp Tester");
          setVal(emailInput, "${testEmail}");
          setVal(phoneInput, "${testPhone}");
          setVal(passInput, "ValidPass@123");
          
          const submitBtn = document.querySelector('form button[type="submit"]');
          if (submitBtn) submitBtn.click();
        })()
      `
    });
    await sleep(4000);

    const auditResults = [];

    for (const vp of VIEWPORTS) {
      // Set device emulation
      await client.send('Emulation.setDeviceMetricsOverride', {
        width: vp.width,
        height: vp.height,
        deviceScaleFactor: vp.deviceScaleFactor,
        mobile: vp.mobile
      });
      await sleep(1000);

      // Measure dimensions, overflow, and layout
      const metrics = await client.send('Runtime.evaluate', {
        expression: `
          (() => {
            const body = document.body;
            const html = document.documentElement;
            const scrollWidth = Math.max(body.scrollWidth, html.scrollWidth);
            const clientWidth = html.clientWidth;
            const innerWidth = window.innerWidth;
            const hasHorizontalOverflow = scrollWidth > (innerWidth + 2); // 2px margin of error
            
            // Check header elements
            const header = document.querySelector('header');
            const hasHeader = !!header;
            const navLinks = Array.from(document.querySelectorAll('header a')).map(a => a.textContent.trim());
            
            return {
              viewportWidth: innerWidth,
              clientWidth: clientWidth,
              scrollWidth: scrollWidth,
              hasHorizontalOverflow,
              hasHeader,
              headerNavCount: navLinks.length,
              elementsCount: document.querySelectorAll('*').length
            };
          })()
        `,
        returnByValue: true
      });

      const res = metrics.result.value;
      const passed = !res.hasHorizontalOverflow && res.hasHeader;
      auditResults.push({
        viewport: vp.name,
        resolution: `${vp.width}x${vp.height}`,
        passed,
        details: res
      });

      console.log(`[${passed ? 'PASS' : 'FAIL'}] ${vp.name.padEnd(32)} (${vp.width}x${vp.height}) | Overflow: ${res.hasHorizontalOverflow ? 'YES (Defect)' : 'NO (Clean)'} | Header: ${res.hasHeader ? 'Present' : 'Missing'}`);
    }

    client.close();
    chromeProc.kill('SIGTERM');

    console.log("======================================================================");
    const allPassed = auditResults.every(r => r.passed);
    console.log(`VIEWPORT AUDIT SUMMARY: ${auditResults.filter(r => r.passed).length}/${auditResults.length} PASSED`);
    console.log(`OVERALL RESULT: ${allPassed ? 'ALL VIEWPORTS PASS - 0 OVERFLOWS DETECTED' : 'FAILURES DETECTED'}`);
    console.log("======================================================================");

    process.exit(allPassed ? 0 : 1);
  } catch (err) {
    console.error("Audit error:", err);
    chromeProc.kill('SIGTERM');
    process.exit(1);
  }
}

runResponsiveAudit();
