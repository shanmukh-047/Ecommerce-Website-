import { spawn } from 'child_process';
import http from 'http';

const CHROME_BIN = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9253;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

async function waitForChrome(port, maxTries = 30) {
  for (let i = 0; i < maxTries; i++) {
    try {
      const data = await fetchJson(`http://127.0.0.1:${port}/json/list`);
      if (Array.isArray(data) && data.length > 0) return data;
    } catch (e) {
      await sleep(300);
    }
  }
  throw new Error(`Chrome debugging port ${port} did not become ready`);
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
  }
  ready() {
    return new Promise((resolve, reject) => {
      if (this.ws.readyState === WebSocket.OPEN) return resolve();
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
    });
  }
  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = this.id++;
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() {
    this.ws.close();
  }
}

async function reproduce() {
  const chromeProc = spawn(CHROME_BIN, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--user-data-dir=/tmp/chrome_reproduce_' + Date.now()
  ]);

  try {
    const list = await waitForChrome(PORT);
    const pageTarget = list.find(t => t.type === 'page');
    if (!pageTarget) throw new Error('No page target found');

    const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
    await cdp.ready();

    await cdp.send('Network.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Log.enable');

    const networkEvents = [];
    const consoleLogs = [];

    cdp.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && cdp.callbacks.has(msg.id)) {
        const { resolve, reject } = cdp.callbacks.get(msg.id);
        cdp.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      } else if (msg.method === 'Network.requestWillBeSent') {
        networkEvents.push({
          type: 'request',
          reqId: msg.params.requestId,
          url: msg.params.request.url,
          method: msg.params.request.method,
          postData: msg.params.request.postData,
          headers: msg.params.request.headers,
        });
      } else if (msg.method === 'Network.responseReceived') {
        networkEvents.push({
          type: 'response',
          reqId: msg.params.requestId,
          url: msg.params.response.url,
          status: msg.params.response.status,
          headers: msg.params.response.headers,
        });
      } else if (msg.method === 'Network.loadingFailed') {
        networkEvents.push({
          type: 'failed',
          reqId: msg.params.requestId,
          errorText: msg.params.errorText,
          canceled: msg.params.canceled,
        });
      } else if (msg.method === 'Runtime.consoleAPICalled') {
        consoleLogs.push({
          type: msg.params.type,
          text: msg.params.args.map((a) => a.value || a.description || JSON.stringify(a)).join(' '),
        });
      }
    };

    console.log('[STEP 1] Navigating to http://localhost:3000');
    await cdp.send('Page.navigate', { url: 'http://localhost:3000' });
    await sleep(2500);

    console.log('[STEP 2] Skipping intro if present');
    await cdp.send('Runtime.evaluate', {
      expression: `document.querySelector('button[aria-label="Skip to store authentication"]')?.click()`,
    });
    await sleep(1500);

    console.log('[STEP 3] Clicking "Create Account" tab on StorefrontAuth');
    await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const buttons = Array.from(document.querySelectorAll('button'));
        const regTab = buttons.find(b => b.innerText.includes('Create Account'));
        if (regTab) regTab.click();
      })()`,
    });
    await sleep(1000);

    const testEmail = `test_fresh_${Date.now()}@example.com`;
    console.log(`[STEP 4] Filling registration form with email: ${testEmail}`);
    await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const inputs = Array.from(document.querySelectorAll('input'));
        const nameInput = inputs.find(i => i.placeholder?.includes('Arun') || i.name === 'full_name' || i.name === 'first_name');
        const emailInput = inputs.find(i => i.type === 'email' || i.name === 'email');
        const phoneInput = inputs.find(i => i.type === 'tel' || i.name === 'phone' || i.name === 'phone_number');
        const passInput = inputs.find(i => i.type === 'password');
        const submitBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Create Account') && b.type === 'submit');

        const setVal = (input, val) => {
          if (!input) return;
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, val);
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        };

        setVal(nameInput, 'Fresh Test User');
        setVal(emailInput, '${testEmail}');
        setVal(phoneInput, '9876543210');
        setVal(passInput, 'FreshTest@12345');

        if (submitBtn) {
          submitBtn.click();
        }
      })()`,
    });
    await sleep(3500);

    console.log('[STEP 5] Inspecting UI state and visible errors');
    const uiState = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify({
        bodyText: document.body.innerText.slice(0, 500),
        alerts: Array.from(document.querySelectorAll('[role="alert"]')).map(a => a.innerText),
        errorElements: Array.from(document.querySelectorAll('.text-red-500, .text-red-600, .text-red-700')).map(e => e.innerText),
      })`,
    });
    const parsedUi = JSON.parse(uiState.result.value);
    console.log('UI State:', parsedUi);

    console.log('\n--- NETWORK EVENTS ---');
    for (const evt of networkEvents) {
      if (evt.url?.includes('/api/v1/') || evt.type === 'failed') {
        console.log(JSON.stringify(evt, null, 2));
      }
    }

    console.log('\n--- CONSOLE LOGS ---');
    for (const log of consoleLogs) {
      console.log(`[${log.type}] ${log.text}`);
    }

    cdp.close();
  } finally {
    chromeProc.kill();
  }
}

reproduce().catch(console.error);
