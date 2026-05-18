// Set to 'http://localhost:8000' for local development
const BACKEND_URL = 'https://cyberboyai.onrender.com';

document.addEventListener('DOMContentLoaded', function() {
  const scanBtn = document.getElementById('scan-btn');
  const loadingDiv = document.getElementById('loading');
  const resultDiv = document.getElementById('result');
  const errorDiv = document.getElementById('error');

  scanBtn.addEventListener('click', async () => {
    // Hide UI
    scanBtn.style.display = 'none';
    resultDiv.classList.add('hidden');
    errorDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');

    try {
      // Get current tab URL
      let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.url) throw new Error("Could not read tab URL.");

      // Check if the user is on a known webmail client
      const isWebmail = tab.url.includes("mail.google.com") || 
                        tab.url.includes("outlook.live.com") || 
                        tab.url.includes("outlook.office.com") ||
                        tab.url.includes("mail.yahoo.com");

      let payload = tab.url; // Default to scanning the website URL itself
      
      // Only perform Deep DOM extraction if we are inside a webmail inbox
      if (isWebmail) {
        let pageText = "";
        try {
          const injectionResults = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => {
              const text = document.body.innerText;
              // Extract all links on the page, filtering out the email provider's own navigation links
              const links = Array.from(document.querySelectorAll('a'))
                .map(a => a.href)
                .filter(href => href.startsWith('http') && 
                               !href.includes('google.com') && 
                               !href.includes('yahoo.com') && 
                               !href.includes('live.com') &&
                               !href.includes('office.com'));
              const uniqueLinks = [...new Set(links)];
              return { text: text, links: uniqueLinks };
            }
          });
          
          if (injectionResults && injectionResults[0] && injectionResults[0].result) {
            const res = injectionResults[0].result;
            pageText = res.text.substring(0, 5000); 
            if (res.links.length > 0) {
               pageText += "\n\n[Embedded Links Found:]\n" + res.links.join("\n");
            }
          }
        } catch (e) {
          console.warn("Could not extract page text:", e);
        }

        if (pageText.length > 50) {
          payload = pageText; // Send the extracted email body
        }
      }

      // Call Backend
      const response = await fetch(`${BACKEND_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: payload, source: 'extension' })
      });

      if (!response.ok) throw new Error("Backend error");

      const data = await response.json();
      displayResult(data, tab.url);
    } catch (err) {
      console.error(err);
      loadingDiv.classList.add('hidden');
      errorDiv.classList.remove('hidden');
      scanBtn.style.display = 'block';
    }
  });

  function displayResult(data, url) {
    loadingDiv.classList.add('hidden');
    resultDiv.classList.remove('hidden');
    scanBtn.style.display = 'block';
    scanBtn.textContent = 'Re-Scan Page';

    document.getElementById('scanned-url').textContent = url.length > 50 ? url.substring(0, 47) + '...' : url;

    const banner = document.getElementById('verdict-banner');
    const title = document.getElementById('verdict-title');
    const confidence = document.getElementById('confidence');
    
    title.textContent = data.verdict;
    let confValue = data.verdict === 'SAFE' ? (1 - data.score) * 100 : data.score * 100;
    confidence.textContent = Math.round(confValue) + '%';

    banner.className = 'banner ' + data.verdict.toLowerCase().replace(" ", "-");

    document.getElementById('explanation').textContent = data.explanation;
    document.getElementById('threat-type').textContent = data.threat_type || 'benign';
    document.getElementById('processing-time').textContent = data.processing_ms + 'ms';
    document.getElementById('advice').textContent = data.advice;

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
  }
});
