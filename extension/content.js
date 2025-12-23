// Sidebar UI injection and transcript logic
(function() {
    'use strict';
  
    // Wait for YouTube to load
    function waitForYouTube(callback) {
      if (window.location.href.includes('/watch?v=')) {
        const observer = new MutationObserver(() => {
          if (document.querySelector('video')) {
            observer.disconnect();
            callback();
          }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(callback, 3500);  // Slightly longer fallback for stability
      } else {
        return;
      }
    }
  
    // Inject sidebar HTML + CSS (always returns the sidebar element)
    function injectSidebar() {
      let sidebar = document.getElementById('transcript-sidebar');
      if (sidebar) return sidebar;  // Return existing if present
  
      sidebar = document.createElement('div');
      sidebar.id = 'transcript-sidebar';
      sidebar.innerHTML = `
        <div class="sidebar-header">
          <div class="icon">T</div>
          <h3>Transcript Copier</h3>
          <button class="close-btn">&times;</button>
        </div>
        <p class="description">Copy clean transcripts (no timestamps) or video title from YouTube.</p>
        <div id="warning" class="warning hidden"></div>
        <div id="status" class="status"></div>
        <button id="copyBtn" class="copy-btn">
          <span class="icon">⟳</span>
          Copy Transcript (No Timestamps)
        </button>
        <button id="titleBtn" class="copy-btn" style="margin-top: 8px;">
          <span class="icon">📋</span>
          Copy Title
        </button>
      `;
  
      // Inline styles (like NoteGPT: clean, blue, rounded)
      sidebar.style.cssText = `
        position: fixed; right: 20px; top: 50%; transform: translateY(-50%);
        width: 350px; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        z-index: 10000; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        padding: 0; border: 1px solid #e0e0e0;
      `;
  
      // Add internal styles via <style> tag (only once)
      if (!document.getElementById('transcript-styles')) {
        const style = document.createElement('style');
        style.id = 'transcript-styles';
        style.textContent = `
          #transcript-sidebar .sidebar-header {
            display: flex; align-items: center; justify-content: space-between; padding: 20px 20px 10px;
            border-bottom: 1px solid #f0f0f0; margin: 0;
          }
          #transcript-sidebar .icon {
            width: 32px; height: 32px; background: #065fd4; border-radius: 50%; color: white;
            display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px;
            margin-right: 10px;
          }
          #transcript-sidebar h3 { margin: 0; color: #065fd4; font-size: 20px; }
          #transcript-sidebar .close-btn {
            background: none; border: none; font-size: 20px; cursor: pointer; color: #666; padding: 0;
            width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
          }
          #transcript-sidebar .close-btn:hover { color: #065fd4; }
          #transcript-sidebar .description {
            color: #666; font-size: 14px; margin: 0 20px 15px; text-align: center;
          }
          #transcript-sidebar .warning {
            background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 12px;
            margin: 0 20px 10px; color: #856404; font-size: 13px; line-height: 1.4;
          }
          #transcript-sidebar .warning.hidden { display: none; }
          #transcript-sidebar .status {
            margin: 10px 20px; font-size: 14px; min-height: 20px; padding: 8px;
            border-radius: 6px; text-align: center;
          }
          #transcript-sidebar .copy-btn {
            background: #065fd4; color: white; border: none; border-radius: 20px; padding: 12px 24px;
            font-size: 14px; font-weight: 500; cursor: pointer; width: calc(100% - 40px); margin: 10px 20px;
            display: flex; align-items: center; justify-content: center; gap: 8px;
          }
          #transcript-sidebar .copy-btn:hover:not(:disabled) { background: #054bb3; }
          #transcript-sidebar .copy-btn:disabled { background: #ccc; cursor: not-allowed; opacity: 0.7; }
          #transcript-sidebar .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
          #transcript-sidebar .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
          #transcript-sidebar .loading { background: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }
          #transcript-sidebar .icon { font-size: 16px; }
        `;
        document.head.appendChild(style);
      }
  
      document.body.appendChild(sidebar);
  
      return sidebar;
    }
  
    // Check captions availability (lightweight)
    async function checkCaptionsAvailability() {
      const videoId = new URLSearchParams(window.location.search).get('v');
      if (!videoId) return false;
  
      try {
        const htmlResponse = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
        const html = await htmlResponse.text();
        const apiKeyMatch = html.match(/"INNERTUBE_API_KEY":"([^"]+)"/);
        if (!apiKeyMatch) return false;
        const apiKey = apiKeyMatch[1];
  
        const playerEndpoint = `https://www.youtube.com/youtubei/v1/player?key=${apiKey}`;
        const playerResponse = await fetch(playerEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            context: { client: { clientName: 'WEB', clientVersion: '2.20251031.00.00' } },
            videoId: videoId,
          }),
        });
        const player = await playerResponse.json();
        const tracks = player.captions?.playerCaptionsTracklistRenderer?.captionTracks || [];
        return tracks.length > 0;
      } catch {
        return false;
      }
    }
  
    // Get full transcript
    async function retrieveTranscript() {
      const videoId = new URLSearchParams(window.location.search).get('v');
      if (!videoId) throw new Error('Not on a valid YouTube video page');
  
      const htmlResponse = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
      const html = await htmlResponse.text();
      const apiKeyMatch = html.match(/"INNERTUBE_API_KEY":"([^"]+)"/);
      if (!apiKeyMatch) throw new Error('API key not found');
      const apiKey = apiKeyMatch[1];
  
      const playerEndpoint = `https://www.youtube.com/youtubei/v1/player?key=${apiKey}`;
      const playerResponse = await fetch(playerEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: { client: { clientName: 'WEB', clientVersion: '2.20251031.00.00' } },
          videoId: videoId,
        }),
      });
      if (!playerResponse.ok) throw new Error(`Player API failed: ${playerResponse.status}`);
      const player = await playerResponse.json();
  
      const tracks = player.captions?.playerCaptionsTracklistRenderer?.captionTracks || [];
      if (tracks.length === 0) throw new Error('No captions available. Enable them with the CC button.');
      tracks.sort((a, b) => {
        if (a.languageCode === 'en' && b.languageCode !== 'en') return -1;
        if (a.languageCode !== 'en' && b.languageCode === 'en') return 1;
        if (a.kind !== 'asr' && b.kind === 'asr') return -1;
        if (a.kind === 'asr' && b.kind !== 'asr') return 1;
        return 0;
      });
  
      const transcriptResponse = await fetch(`${tracks[0].baseUrl}&fmt=json3`);
      if (!transcriptResponse.ok) throw new Error(`Transcript fetch failed: ${transcriptResponse.status}`);
      const transcriptData = await transcriptResponse.json();
  
      const cleanTranscript = transcriptData.events
        .filter(event => event.segs)
        .map(event => event.segs.map(seg => seg.utf8).join(' ').trim())
        .filter(line => line.length > 0)
        .join('\n');
  
      if (!cleanTranscript) throw new Error('Transcript is empty');
      return cleanTranscript;
    }
  
    // Get video title (from player response)
    async function getVideoTitle() {
      const videoId = new URLSearchParams(window.location.search).get('v');
      if (!videoId) throw new Error('Not on a valid YouTube video page');
  
      const htmlResponse = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
      const html = await htmlResponse.text();
      const apiKeyMatch = html.match(/"INNERTUBE_API_KEY":"([^"]+)"/);
      if (!apiKeyMatch) throw new Error('API key not found');
      const apiKey = apiKeyMatch[1];
  
      const playerEndpoint = `https://www.youtube.com/youtubei/v1/player?key=${apiKey}`;
      const playerResponse = await fetch(playerEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: { client: { clientName: 'WEB', clientVersion: '2.20251031.00.00' } },
          videoId: videoId,
        }),
      });
      if (!playerResponse.ok) throw new Error(`Player API failed: ${playerResponse.status}`);
      const player = await playerResponse.json();
  
      const title = player.videoDetails?.title;
      if (!title) throw new Error('Title not found');
      return title;
    }
  
    // Copy to clipboard with fallback (error-proofed)
    async function copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (err) {
        // Fallback only if DOM is ready
        if (typeof document === 'undefined' || !document.body) {
          console.warn('Clipboard fallback unavailable (DOM not ready)');
          return false;
        }
        try {
          const textarea = document.createElement('textarea');
          textarea.value = text;
          textarea.style.position = 'fixed';  // Off-screen to avoid flash
          textarea.style.left = '-9999px';
          document.body.appendChild(textarea);
          textarea.focus();
          textarea.select();
          const success = document.execCommand('copy');
          document.body.removeChild(textarea);
          return success;
        } catch (fallbackErr) {
          console.error('Fallback copy failed:', fallbackErr);
          return false;
        }
      }
    }
  
    // Initialize UI logic (run only once)
    function initUI() {
      if (window.transcriptInitDone) return;  // Prevent duplicate runs
      window.transcriptInitDone = true;
  
      const sidebar = injectSidebar();
      if (!sidebar) return;  // Safety check
  
      const copyBtn = sidebar.querySelector('#copyBtn');
      const titleBtn = sidebar.querySelector('#titleBtn');
      const status = sidebar.querySelector('#status');
      const warning = sidebar.querySelector('#warning');
      const closeBtn = sidebar.querySelector('.close-btn');
  
      if (!copyBtn || !titleBtn || !status || !warning || !closeBtn) return;  // Safety check
  
      function updateStatus(msg, className = '') {
        status.textContent = msg;
        status.className = className;
      }
  
      function updateWarning(msg) {
        if (msg) {
          warning.textContent = msg;
          warning.classList.remove('hidden');
          copyBtn.disabled = true;
        } else {
          warning.classList.add('hidden');
          copyBtn.disabled = false;
        }
      }
  
      // Pre-check on load
      checkCaptionsAvailability().then(hasCaptions => {
        if (!hasCaptions) {
          updateWarning('No transcript available. Enable captions on the video (CC button under player).');
        }
      });
  
      // Transcript button click
      copyBtn.addEventListener('click', async () => {
        if (copyBtn.disabled) return;
        copyBtn.disabled = true;
        copyBtn.innerHTML = '<span class="icon">⏳</span>Copying...';
        updateStatus('Fetching transcript...', 'loading');
  
        try {
          const transcript = await retrieveTranscript();
          const success = await copyToClipboard(transcript);
          if (success) {
            updateStatus('Transcript copied! Paste with Ctrl+V.', 'success');
            copyBtn.innerHTML = '<span class="icon">✅</span>Copied Transcript!';
            setTimeout(() => {
              copyBtn.innerHTML = '<span class="icon">⟳</span>Copy Transcript (No Timestamps)';
              copyBtn.disabled = false;
              updateStatus('');
            }, 2000);
          } else {
            throw new Error('Copy failed');
          }
        } catch (error) {
          updateStatus(error.message, 'error');
          copyBtn.innerHTML = '<span class="icon">⟳</span>Copy Transcript (No Timestamps)';
          copyBtn.disabled = false;
        }
      });
  
      // Title button click
      titleBtn.addEventListener('click', async () => {
        titleBtn.disabled = true;
        titleBtn.innerHTML = '<span class="icon">⏳</span>Copying...';
        updateStatus('Fetching title...', 'loading');
  
        try {
          const title = await getVideoTitle();
          const success = await copyToClipboard(title);
          if (success) {
            updateStatus(`"${title.substring(0, 50)}..." copied!`, 'success');
            titleBtn.innerHTML = '<span class="icon">✅</span>Copied Title!';
            setTimeout(() => {
              titleBtn.innerHTML = '<span class="icon">📋</span>Copy Title';
              titleBtn.disabled = false;
              updateStatus('');
            }, 2000);
          } else {
            throw new Error('Copy failed');
          }
        } catch (error) {
          updateStatus(error.message, 'error');
          titleBtn.innerHTML = '<span class="icon">📋</span>Copy Title';
          titleBtn.disabled = false;
        }
      });
  
      // Close button toggle (attach only once)
      if (!closeBtn.hasAttribute('data-listener-added')) {
        closeBtn.setAttribute('data-listener-added', 'true');
        closeBtn.addEventListener('click', () => {
          sidebar.style.display = 'none';
          // Add a small toggle icon in top-right for reopen
          let toggleIcon = document.getElementById('transcript-toggle');
          if (!toggleIcon) {
            toggleIcon = document.createElement('div');
            toggleIcon.id = 'transcript-toggle';
            toggleIcon.innerHTML = 'T';
            toggleIcon.style.cssText = `
              position: fixed; right: 20px; top: 20px; width: 40px; height: 40px; background: #065fd4;
              border-radius: 50%; color: white; display: flex; align-items: center; justify-content: center;
              font-weight: bold; font-size: 18px; cursor: pointer; z-index: 10001; box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            `;
            toggleIcon.addEventListener('click', () => {
              sidebar.style.display = 'block';
              toggleIcon.style.display = 'none';
            });
            document.body.appendChild(toggleIcon);
          }
          toggleIcon.style.display = 'flex';
        });
      }
    }
  
    // Run when ready
    waitForYouTube(initUI);
  })();