import { spawn } from 'child_process';
import http from 'http';

const CHROME_BIN = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9244;

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

async function diagnosePage(url, pageName) {
  console.log(`\n==================================================`);
  console.log(`DIAGNOSING RUNTIME: ${pageName} -> ${url}`);
  console.log(`==================================================`);

  const chromeProc = spawn(CHROME_BIN, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--user-data-dir=/tmp/chrome_diag_' + Date.now()
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

    const requests = new Map();
    const networkFailures = [];
    const consoleLogs = [];
    const consoleErrors = [];

    cdp.events = [];
    cdp.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && cdp.callbacks.has(msg.id)) {
        const { resolve, reject } = cdp.callbacks.get(msg.id);
        cdp.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      } else if (msg.method === 'Network.requestWillBeSent') {
        requests.set(msg.params.requestId, {
          url: msg.params.request.url,
          method: msg.params.request.method,
          headers: msg.params.request.headers,
          initiator: msg.params.initiator?.type,
        });
      } else if (msg.method === 'Network.responseReceived') {
        const req = requests.get(msg.params.requestId);
        if (req) {
          req.status = msg.params.response.status;
          req.statusText = msg.params.response.statusText;
          req.mimeType = msg.params.response.mimeType;
          req.responseHeaders = msg.params.response.headers;
        }
      } else if (msg.method === 'Network.loadingFailed') {
        const req = requests.get(msg.params.requestId);
        networkFailures.push({
          url: req?.url || 'unknown',
          errorText: msg.params.errorText,
          canceled: msg.params.canceled,
        });
      } else if (msg.method === 'Runtime.consoleAPICalled') {
        const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
        consoleLogs.push(`[${msg.params.type}] ${text}`);
        if (msg.params.type === 'error' || msg.params.type === 'warning') {
          consoleErrors.push(`[${msg.params.type}] ${text}`);
        }
      } else if (msg.method === 'Runtime.exceptionThrown') {
        consoleErrors.push(`[exception] ${msg.params.exceptionDetails?.text} ${msg.params.exceptionDetails?.exception?.description || ''}`);
      }
    };

    await cdp.send('Page.navigate', { url });
    await sleep(4000);

    console.log(`Total Requests: ${requests.size}`);
    for (const [id, req] of requests.entries()) {
      if (req.url.includes('/api/v1/') || req.url.includes(':8000')) {
        console.log(`API REQ: ${req.method} ${req.url} -> Status: ${req.status || 'NO_RESPONSE'}`);
      }
    }

    if (networkFailures.length > 0) {
      console.log(`\nNetwork Failures (${networkFailures.length}):`);
      for (const nf of networkFailures) {
        console.log(`  FAILED: ${nf.url} - ${nf.errorText} (canceled: ${nf.canceled})`);
      }
    } else {
      console.log(`Network Failures: 0`);
    }

    if (consoleErrors.length > 0) {
      console.log(`\nConsole Errors/Warnings (${consoleErrors.length}):`);
      for (const ce of consoleErrors) {
        console.log(`  ${ce}`);
      }
    } else {
      console.log(`Console Errors/Warnings: 0`);
    }

    // Check DOM content
    const evalRes = await cdp.send('Runtime.evaluate', {
      expression: `JSON.stringify({
        title: document.title,
        bodyTextSnippet: document.body.innerText.slice(0, 300),
        productCards: document.querySelectorAll('[data-testid="product-card"], .product-card, [href^="/products/"]').length,
        hasFailedToFetch: document.body.innerText.includes('Failed to fetch'),
        errorsOnPage: Array.from(document.querySelectorAll('.text-red-500, .text-red-600, [role="alert"]')).map(el => el.innerText)
      })`
    });

    const pageState = JSON.parse(evalRes.result.value);
    console.log(`\nPage State:`, pageState);

    cdp.close();
  } finally {
    chromeProc.kill();
  }
}

async function run() {
  await diagnosePage('http://localhost:3000', 'Homepage');
  await diagnosePage('http://localhost:3000/products', 'Products Page');
  await diagnosePage('http://localhost:3000/login', 'Login Page');
}

run().catch(console.error);
