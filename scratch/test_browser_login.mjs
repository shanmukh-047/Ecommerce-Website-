import { spawn } from 'child_process';
import http from 'http';

const CHROME_BIN = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9245;

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

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
    this.events = [];
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      } else if (msg.method) {
        this.events.push(msg);
      }
    };
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

async function testLogin(email, password, label) {
  console.log(`\n==================================================`);
  console.log(`TESTING BROWSER LOGIN: ${label} (${email})`);
  console.log(`==================================================`);

  const chromeProc = spawn(CHROME_BIN, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--user-data-dir=/tmp/chrome_login_' + Date.now()
  ]);

  await sleep(1200);

  try {
    const list = await fetchJson(`http://127.0.0.1:${PORT}/json/list`);
    const page = list.find(t => t.type === 'page');
    if (!page) throw new Error('No page target found');

    const cdp = new CDPClient(page.webSocketDebuggerUrl);
    await cdp.ready();

    await cdp.send('Network.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Log.enable');

    const requests = [];
    const consoleLogs = [];

    cdp.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && cdp.callbacks.has(msg.id)) {
        const { resolve, reject } = cdp.callbacks.get(msg.id);
        cdp.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      } else if (msg.method === 'Network.requestWillBeSent') {
        if (msg.params.request.url.includes('/api/v1/')) {
          requests.push({
            url: msg.params.request.url,
            method: msg.params.request.method,
            postData: msg.params.request.postData,
            headers: msg.params.request.headers
          });
        }
      } else if (msg.method === 'Network.responseReceived') {
        const req = requests.find(r => r.url === msg.params.response.url);
        if (req) {
          req.status = msg.params.response.status;
          req.statusText = msg.params.response.statusText;
        }
      } else if (msg.method === 'Runtime.consoleAPICalled') {
        const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
        consoleLogs.push(`[${msg.params.type}] ${text}`);
      }
    };

    await cdp.send('Page.navigate', { url: 'http://localhost:3000/login' });
    await sleep(2500);

    // Enter email & password and click Sign In
    const fillResult = await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        const emailInput = document.querySelector('input[name="email"], input[type="email"]');
        const passInput = document.querySelector('input[name="password"], input[type="password"]');
        const submitBtn = document.querySelector('button[type="submit"]');

        if (!emailInput || !passInput || !submitBtn) {
          return { error: 'Form elements not found' };
        }

        // Use native value setter for React controlled input
        const setVal = (input, val) => {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, val);
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        };

        setVal(emailInput, ${JSON.stringify(email)});
        setVal(passInput, ${JSON.stringify(password)});

        submitBtn.click();
        return { success: true };
      })()`
    });

    console.log('Form fill result:', fillResult.result.value);
    await sleep(4000);

    console.log('\nAPI Requests Triggered:');
    for (const r of requests) {
      console.log(`  ${r.method} ${r.url} -> Status: ${r.status || 'PENDING'}`);
      if (r.postData) console.log(`    Payload: ${r.postData}`);
    }

    console.log('\nConsole Logs:');
    for (const cl of consoleLogs) {
      console.log(`  ${cl}`);
    }

    const state = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify({
        url: window.location.href,
        pathname: window.location.pathname,
        hasAlert: !!document.querySelector('[role="alert"]'),
        alertText: document.querySelector('[role="alert"]')?.innerText || null,
        bodySnippet: document.body.innerText.slice(0, 300)
      })`
    });

    console.log('\nFinal Page State:', JSON.parse(state.result.value));

    cdp.close();
  } finally {
    chromeProc.kill();
  }
}

async function run() {
  await testLogin('testuser@example.com', 'WrongPassword123!', 'Invalid Credentials');
  await testLogin('testuser@example.com', 'Test@12345', 'Valid Credentials');
}

run().catch(console.error);
