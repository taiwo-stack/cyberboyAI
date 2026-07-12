// Set to local or API Gateway HTTPS endpoint
const BACKEND_URL = 'https://phzuhhvgvj.execute-api.us-east-1.amazonaws.com';

document.addEventListener('DOMContentLoaded', function() {
  const scanBtn = document.getElementById('scan-btn');
  const loadingDiv = document.getElementById('loading');
  const resultDiv = document.getElementById('result');
  const errorDiv = document.getElementById('error');

  // ── Context-menu auto-scan ───────────────────────────────────────────────────
  // When the user right-clicked and chose "Analyze with GaudOn", background.js
  // stored the selected text/URL in chrome.storage.local before opening this popup.
  // We pick it up here, run the scan immediately, then clear the entry so stale
  // data never fires on a future manual popup open.
  chrome.storage.local.get("gaudOn_pending", async (stored) => {
    const pending = stored.gaudOn_pending;
    const STALE_MS = 30_000; // ignore entries older than 30 s
    if (pending && pending.input && (Date.now() - pending.timestamp) < STALE_MS) {
      chrome.storage.local.remove("gaudOn_pending");
      // Build a clean human-readable label for the scanned-url field.
      // If input looks like a URL use it directly; otherwise describe the selection.
      const inp = pending.input;
      const isUrl = /^https?:\/\//i.test(inp) || (/^[\w-]+\.\w{2,}/.test(inp) && inp.length < 100);
      const label = isUrl
        ? (inp.length > 60 ? inp.substring(0, 57) + '...' : inp)
        : `Selected text (${inp.length} chars)`;
      await runScan(inp, label);
    }
  });

  // ── Manual scan button ───────────────────────────────────────────────────────
  scanBtn.addEventListener('click', async () => {
    try {
      let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.url) throw new Error("Could not read tab URL.");

      let payload = tab.url; // default: scan the page URL

      // Try to inject DOM content extractor (selection or webmail body)
      let extractedContent = null;
      const isRestricted = !tab.url || 
                           tab.url.startsWith("chrome://") || 
                           tab.url.startsWith("chrome-extension://") || 
                           tab.url.startsWith("about:") || 
                           tab.url.includes("chrome.google.com/webstore");

      if (!isRestricted) {
        try {
          const injectionResults = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
          func: () => {
            const excludedDomains = ['google.com', 'yahoo.com', 'live.com', 'office.com'];

            const extractLinks = (containerEl) => {
              const urls = [];
              
              // 1. Standard anchors
              containerEl.querySelectorAll('a').forEach(a => {
                if (a.href) urls.push(a.href);
              });
              
              // 2. Form action endpoints (often used in malicious buttons/phishing mail)
              containerEl.querySelectorAll('form[action]').forEach(form => {
                if (form.action) urls.push(form.action);
              });
              
              // 3. Custom attributes for custom redirection elements
              containerEl.querySelectorAll('[data-href], [data-url], [data-link]').forEach(el => {
                const url = el.getAttribute('data-href') || el.getAttribute('data-url') || el.getAttribute('data-link');
                if (url) urls.push(url);
              });
              
              // 4. Inline Javascript redirections
              containerEl.querySelectorAll('[onclick]').forEach(el => {
                const clickAttr = el.getAttribute('onclick');
                if (clickAttr) {
                  const match = clickAttr.match(/(https?:\/\/[^\s'"]+)/i);
                  if (match) urls.push(match[0]);
                }
              });

              // Process, validate, filter
              return [...new Set(urls)]
                .map(url => url.trim())
                .filter(url => {
                  try {
                    const parsed = new URL(url);
                    if (!parsed.protocol.startsWith('http')) return false;
                    const host = parsed.hostname.toLowerCase();
                    return !excludedDomains.some(d => host === d || host.endsWith('.' + d));
                  } catch (e) {
                    if (!url.startsWith('http')) return false;
                    const urlLower = url.toLowerCase();
                    return !excludedDomains.some(d => urlLower.includes(d));
                  }
                });
            };

            // 1. Highlighted text — highest priority
            const selection = window.getSelection().toString().trim();
            if (selection.length > 10) {
              let selectionLinks = [];
              try {
                const range = window.getSelection().getRangeAt(0);
                const container = document.createElement("div");
                container.appendChild(range.cloneContents());
                selectionLinks = extractLinks(container);
              } catch (err) {}
              return { text: selection, links: selectionLinks, type: "selection" };
            }

            // 2. Webmail body isolation
            const host = window.location.hostname;
            let emailText = "";
            let emailLinks = [];

            if (host.includes("mail.google.com")) {
              const els = document.querySelectorAll('.a3s, .ii.gt, div[role="listitem"] div.a3s');
              els.forEach(el => {
                emailText += el.innerText + "\n";
                extractLinks(el).forEach(h => emailLinks.push(h));
              });
            } else if (host.includes("outlook.live.com") || host.includes("outlook.office.com")) {
              const els = document.querySelectorAll('div[role="document"], div[aria-label="Email message body"], .ReadingPane');
              els.forEach(el => {
                emailText += el.innerText + "\n";
                extractLinks(el).forEach(h => emailLinks.push(h));
              });
            } else if (host.includes("mail.yahoo.com")) {
              const els = document.querySelectorAll('div[data-test-id="message-view-body"], .thread-body');
              els.forEach(el => {
                emailText += el.innerText + "\n";
                extractLinks(el).forEach(h => emailLinks.push(h));
              });
            }

            if (emailText.trim().length > 20) {
              return { text: emailText.trim(), links: [...new Set(emailLinks)], type: "webmail" };
            }

            return null;
          }
        });

        if (injectionResults && injectionResults[0] && injectionResults[0].result) {
          extractedContent = injectionResults[0].result;
        }
      } catch (e) {
        console.warn("Could not inject scraper:", e);
      }
    }

      if (extractedContent) {
        let finalPayload = extractedContent.text;
        if (extractedContent.links.length > 0) {
          finalPayload += "\n\n[Embedded Links Found:]\n" + extractedContent.links.join("\n");
        }
        if (finalPayload.length > 30) payload = finalPayload;
      }

      await runScan(payload, tab.url);
    } catch (err) {
      console.error(err);
      showError();
    }
  });

  // ── Accordion toggle ─────────────────────────────────────────────────────────
  const toggleDetailsBtn = document.getElementById('toggle-details');
  const detailsPanel = document.getElementById('details-panel');
  if (toggleDetailsBtn) {
    toggleDetailsBtn.addEventListener('click', () => {
      const isHidden = detailsPanel.classList.toggle('hidden');
      toggleDetailsBtn.classList.toggle('active', !isHidden);
    });
  }

  // ── Shared scan runner ───────────────────────────────────────────────────────
  // Called by both the button click and the context-menu auto-trigger.
  // `input`      — the text / URL / email body to analyse
  // `displayUrl` — the label shown in the scanned-url box (the raw tab URL or
  //               a truncated version of selected text)
  async function runScan(input, displayUrl) {
    // Show loading state
    scanBtn.style.display = 'none';
    resultDiv.classList.add('hidden');
    errorDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');

    try {
      const response = await fetch(`${BACKEND_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: input, source: 'extension' })
      });

      if (!response.ok) throw new Error(`Backend error ${response.status}`);

      const data = await response.json();
      displayResult(data, displayUrl);
    } catch (err) {
      console.error(err);
      showError();
    }
  }

  function showError() {
    loadingDiv.classList.add('hidden');
    errorDiv.classList.remove('hidden');
    scanBtn.style.display = 'block';
    scanBtn.textContent = 'Scan Current Page';
  }

  // ── Result renderer ──────────────────────────────────────────────────────────
  function displayResult(data, url) {
    loadingDiv.classList.add('hidden');
    resultDiv.classList.remove('hidden');
    scanBtn.style.display = 'block';
    scanBtn.textContent = 'Re-Scan Page';

    // Scanned URL label — truncate long selected text to 60 chars
    const label = url.length > 60 ? url.substring(0, 57) + '...' : url;
    document.getElementById('scanned-url').textContent = label;

    const banner = document.getElementById('verdict-banner');
    const title = document.getElementById('verdict-title');
    const confidence = document.getElementById('confidence');

    title.textContent = data.verdict;
    const confValue = data.verdict === 'SAFE' ? (1 - data.score) * 100 : data.score * 100;
    confidence.textContent = Math.round(confValue) + '%';
    banner.className = 'banner ' + data.verdict.toLowerCase().replace(" ", "-");

    document.getElementById('explanation').textContent = data.explanation;
    document.getElementById('threat-type').textContent = data.threat_type || 'benign';
    document.getElementById('processing-time').textContent = data.processing_ms + 'ms';
    document.getElementById('advice').textContent = data.advice;

    // Red flags
    const redFlagsList = document.getElementById('red-flags-list');
    const redFlagsContainer = document.getElementById('red-flags-container');
    redFlagsList.innerHTML = '';
    if (data.red_flags && data.red_flags.length > 0) {
      redFlagsContainer.classList.remove('hidden');
      data.red_flags.forEach(flag => {
        const li = document.createElement('li');
        li.textContent = flag;
        redFlagsList.appendChild(li);
      });
    } else {
      redFlagsContainer.classList.add('hidden');
    }

    // Technical Deep-Dive — Email content section
    const emailRes = data.email_result;
    const emailSec = document.getElementById('email-section');
    const emailRow = document.getElementById('agent-row-email');
    
    if (emailRes) {
      emailSec.classList.remove('hidden');
      emailRow.classList.remove('hidden');
      document.getElementById('email-threat').textContent = emailRes.threat_type.toUpperCase();
      document.getElementById('email-finding').textContent = emailRes.finding || "No specific patterns flagged.";
    } else {
      emailSec.classList.add('hidden');
      emailRow.classList.add('hidden');
    }

    // Technical Deep-Dive — SSL cert and Redirect Sections
    const behavior = data.behavior_result;
    const sslSec = document.getElementById('ssl-section');
    const redirectSec = document.getElementById('redirect-section');

    if (behavior && (behavior.ssl_issuer !== 'None/Insecure' || (behavior.redirect_chain && behavior.redirect_chain.length > 0))) {
      sslSec.classList.remove('hidden');
      redirectSec.classList.remove('hidden');
      
      document.getElementById('ssl-issuer').textContent   = behavior.ssl_issuer || 'None/Insecure';
      const certValidity = behavior.dynamic_findings?.days_to_expire;
      document.getElementById('ssl-validity').textContent = typeof certValidity === 'number' ? certValidity + ' days remaining' : 'N/A';
      const certAge = behavior.dynamic_findings?.cert_age_days;
      document.getElementById('ssl-age').textContent      = typeof certAge === 'number' ? certAge + ' days old' : 'N/A';

      // Redirect chain
      const redirectList = document.getElementById('redirect-list');
      redirectList.innerHTML = '';
      const chain = behavior.redirect_chain || [];
      if (chain.length > 0) {
        chain.forEach(hop => {
          const li = document.createElement('li');
          li.textContent = hop;
          redirectList.appendChild(li);
        });
      } else {
        const li = document.createElement('li');
        li.textContent = 'No redirects detected. Direct connection.';
        redirectList.appendChild(li);
      }
    } else {
      sslSec.classList.add('hidden');
      redirectSec.classList.add('hidden');
    }

    // Agent score bars
    function updateAgentBar(prefix, score) {
      const bar = document.getElementById(`score-bar-${prefix}`);
      const val = document.getElementById(`score-val-${prefix}`);
      if (!bar || !val) return;
      const scorePct = Math.round((score || 0) * 100);
      bar.style.width = scorePct + '%';
      val.textContent = scorePct + '%';
      bar.className = 'score-bar';
      if (score >= 0.75)      bar.classList.add('dangerous');
      else if (score >= 0.35) bar.classList.add('suspicious');
      else                    bar.classList.add('safe');
    }

    updateAgentBar('email',    data.email_result?.email_score);
    updateAgentBar('brand',    data.brand_result?.similarity_score);
    updateAgentBar('lookup',   data.lookup_result?.db_score);
    updateAgentBar('ml',       data.ml_result?.ml_score);
    updateAgentBar('behavior', data.behavior_result?.behavior_score);
  }
});
