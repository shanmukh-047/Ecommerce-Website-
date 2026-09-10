// scratch/test_phase4_browser_flow.mjs
import { spawn } from 'child_process';

const CHROME_BIN = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9265;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitForChromeTarget(port, maxTries = 30) {
  for (let i = 0; i < maxTries; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/new`, { method: 'PUT' });
      const target = await res.json();
      if (target && target.webSocketDebuggerUrl) {
        return target;
      }
    } catch (e) {
      await sleep(300);
    }
  }
  throw new Error(`Chrome debugging port ${port} did not become ready`);
}

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 1;
    this.callbacks = new Map();
    this.onEvent = null;
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
      } else if (this.onEvent) {
        this.onEvent(msg);
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

async function runPhase4Test() {
  console.log("==================================================");
  console.log("PHASE 4: FRESH BROWSER AUTHENTICATION FLOW TEST");
  console.log("==================================================");

  const chromeProc = spawn(CHROME_BIN, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--user-data-dir=/tmp/chrome_phase4_' + Date.now(),
    'about:blank'
  ]);

  try {
    const pageTarget = await waitForChromeTarget(PORT);
    console.log("Chrome target acquired:", pageTarget.id);

    const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
    await cdp.connect();

    await cdp.send('Network.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Log.enable');

    const consoleErrors = [];
    const failedReqs = [];

    cdp.onEvent = (msg) => {
      if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
        const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
        consoleErrors.push(text);
      } else if (msg.method === 'Network.loadingFailed' && !msg.params.canceled) {
        failedReqs.push(msg.params.errorText);
      }
    };

    // 1. Open Website
    console.log("\n[STEP 1] Open Website (http://localhost:3000)");
    await cdp.send('Page.navigate', { url: 'http://localhost:3000' });
    await sleep(2500);

    // 2. Intro Appears
    const introCheck = await cdp.send('Runtime.evaluate', {
      expression: `!!document.querySelector('[aria-label="Bharat Masala Brand Experience"]')`
    });
    console.log(`Intro rendered: ${introCheck.result.value}`);
    if (!introCheck.result.value) throw new Error("Intro did not appear on fresh session");

    // 3. Skip Intro
    console.log("\n[STEP 2] Skip Intro to reach StorefrontAuth");
    await cdp.send('Runtime.evaluate', {
      expression: `document.querySelector('button[aria-label="Skip to store authentication"]')?.click()`
    });
    await sleep(1500);

    // 4. Switch to Create Account Tab
    console.log("\n[STEP 3] Switch to Create Account Tab");
    await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const buttons = Array.from(document.querySelectorAll('button'));
        const regBtn = buttons.find(b => b.innerText.includes('Create Account'));
        if (regBtn) regBtn.click();
      })()`
    });
    await sleep(1000);

    // 5. Test Invalid Registration (Empty Fields)
    console.log("\n[STEP 4] Test Empty Fields Validation");
    await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const submitBtn = document.querySelector('form button[type="submit"]');
        if (submitBtn) submitBtn.click();
      })()`
    });
    await sleep(500);
    const emptyErrors = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify(Array.from(document.querySelectorAll('.text-feedback-error, [role="alert"]')).map(e => e.innerText).filter(Boolean))`
    });
    const parsedErrors = JSON.parse(emptyErrors.result.value || '[]');
    console.log(`Validation errors on empty submit: ${JSON.stringify(parsedErrors)}`);
    if (parsedErrors.length === 0) throw new Error("Client validation did not trigger on empty fields");

    // 6. Test Valid Registration
    const newCustomerEmail = `cust_phase4_${Date.now()}@example.com`;
    const newCustomerPhone = `98${Math.floor(10000000 + Math.random() * 90000000)}`;
    console.log(`\n[STEP 5] Create Customer Account: ${newCustomerEmail} / ${newCustomerPhone}`);
    
    const fillLog = await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const inputs = Array.from(document.querySelectorAll('input'));
        const nameInput = inputs.find(i => i.name === 'full_name');
        const emailInput = inputs.find(i => i.name === 'email');
        const phoneInput = inputs.find(i => i.name === 'phone_number');
        const passInput = inputs.find(i => i.name === 'password');
        const submitBtn = document.querySelector('form button[type="submit"]');

        const setVal = (input, val) => {
          if (!input) return;
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, val);
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        };

        setVal(nameInput, 'Phase4 Verified Customer');
        setVal(emailInput, '${newCustomerEmail}');
        setVal(phoneInput, '${newCustomerPhone}');
        setVal(passInput, 'CustomerPass@123');

        if (submitBtn) submitBtn.click();

        return JSON.stringify({
          hasName: !!nameInput,
          hasEmail: !!emailInput,
          hasPhone: !!phoneInput,
          hasPass: !!passInput,
          hasSubmit: !!submitBtn,
          emailVal: emailInput?.value,
          phoneVal: phoneInput?.value
        });
      })()`
    });
    console.log("Fill log:", fillLog.result.value);
    await sleep(4000);

    // 7. Verify Registration Success & Storefront Unlocked
    const storeState = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify({
        hasNav: !!document.querySelector('nav, header'),
        hasFailedToFetch: document.body.innerText.includes('Failed to fetch') || document.body.innerText.includes('network connection'),
        productCards: document.querySelectorAll('[href^="/products/"]').length,
        hasToken: !!localStorage.getItem('bharat_access_token'),
        visibleErrors: Array.from(document.querySelectorAll('.text-feedback-error, [role="alert"]')).map(e => e.innerText)
      })`
    });
    const storeData = JSON.parse(storeState.result.value);
    console.log("Storefront Unlocked State:", storeData);
    if (!storeData.hasNav || !storeData.hasToken || storeData.hasFailedToFetch) {
      throw new Error(`Registration failed to unlock store cleanly: ${JSON.stringify(storeData)}`);
    }

    // 8. Open Account Page
    console.log("\n[STEP 6] Open Account Page");
    await cdp.send('Page.navigate', { url: 'http://localhost:3000/account' });
    await sleep(2500);
    const accEmailCheck = await cdp.send('Runtime.evaluate', {
      expression: `document.body.innerText.includes('${newCustomerEmail}')`
    });
    console.log(`Account displays customer email: ${accEmailCheck.result.value}`);
    if (!accEmailCheck.result.value) throw new Error("Account page did not render customer email");

    // 9. Logout
    console.log("\n[STEP 7] Logout");
    await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const signoutBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Sign Out'));
        if (signoutBtn) signoutBtn.click();
      })()`
    });
    await sleep(2500);

    const postLogoutState = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify({
        hasAuthScreen: !!document.querySelector('input[name="username"]'),
        hasToken: !!localStorage.getItem('bharat_access_token')
      })`
    });
    const postLogoutData = JSON.parse(postLogoutState.result.value);
    console.log("Post Logout State:", postLogoutData);
    if (postLogoutData.hasToken || !postLogoutData.hasAuthScreen) {
      throw new Error("Logout did not reset authentication state");
    }

    // 10. Login with newly created account
    console.log("\n[STEP 8] Login with newly created account");
    await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const emailInput = document.querySelector('input[name="username"]');
        const passInput = document.querySelector('input[name="password"]');
        const submitBtn = document.querySelector('button[type="submit"]');

        const setVal = (input, val) => {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, val);
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        };

        setVal(emailInput, '${newCustomerEmail}');
        setVal(passInput, 'CustomerPass@123');
        if (submitBtn) submitBtn.click();
      })()`
    });
    await sleep(3500);

    // 11. Verify Re-authenticated
    const reloginState = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify({
        hasNav: !!document.querySelector('nav, header'),
        hasToken: !!localStorage.getItem('bharat_access_token')
      })`
    });
    const reloginData = JSON.parse(reloginState.result.value);
    console.log("Re-login State:", reloginData);
    if (!reloginData.hasNav || !reloginData.hasToken) {
      throw new Error("Re-login failed");
    }

    // 12. Refresh Page & Verify Persistence
    console.log("\n[STEP 9] Refresh Page & Verify Session Persistence");
    await cdp.send('Page.reload');
    await sleep(2500);
    const reloadState = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify({
        hasNav: !!document.querySelector('nav, header'),
        hasToken: !!localStorage.getItem('bharat_access_token')
      })`
    });
    const reloadData = JSON.parse(reloadState.result.value);
    console.log("Post-Reload State:", reloadData);
    if (!reloadData.hasNav || !reloadData.hasToken) {
      throw new Error("Session was lost on reload");
    }

    console.log("\n==================================================");
    console.log("PHASE 4 COMPLETE BROWSER AUTHENTICATION TEST PASSED!");
    console.log("==================================================");
    cdp.close();
  } finally {
    chromeProc.kill();
  }
}

runPhase4Test().catch(err => {
  console.error("PHASE 4 TEST FAILED:", err);
  process.exit(1);
});
