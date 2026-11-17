// ==UserScript==
// @name         GhostWriter AI - Grok Web Bridge (Auto Text Generator)
// @namespace    https://github.com/naz-ahtamir/ghost_writer
// @version      1.0.0
// @description  Menghubungkan GhostWriter AI langsung ke Web Grok (grok.com & x.com/i/grok) secara gratis tanpa API Key.
// @author       GhostWriter AI
// @match        https://grok.com/*
// @match        https://*.grok.com/*
// @match        https://x.com/i/grok*
// @match        https://twitter.com/i/grok*
// @match        https://openrouter.ai/chat*
// @match        https://openrouter.ai/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    const DEFAULT_PORT = 8788;
    let bridgePort = Number(localStorage.getItem('gw_bridge_port')) || DEFAULT_PORT;
    let isPaused = false;
    let isBusy = false;
    let forceSendRequested = false;
    let currentTaskId = null;

    function getBaseUrl() {
        return `http://127.0.0.1:${bridgePort}`;
    }

    // Cross-origin request wrapper supporting both Tampermonkey GM_xmlhttpRequest and standard fetch
    function bridgeRequest(method, path, bodyObj = null) {
        const url = `${getBaseUrl()}${path}`;
        return new Promise((resolve, reject) => {
            if (typeof GM_xmlhttpRequest === 'function') {
                GM_xmlhttpRequest({
                    method: method,
                    url: url,
                    headers: { 'Content-Type': 'application/json' },
                    data: bodyObj ? JSON.stringify(bodyObj) : undefined,
                    timeout: 8000,
                    onload: (res) => {
                        try {
                            resolve(JSON.parse(res.responseText));
                        } catch (err) {
                            reject(err);
                        }
                    },
                    onerror: (err) => reject(err),
                    ontimeout: () => reject(new Error('timeout')),
                });
            } else {
                fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: bodyObj ? JSON.stringify(bodyObj) : undefined,
                })
                    .then((r) => r.json())
                    .then(resolve)
                    .catch(reject);
            }
        });
    }

    // UI Status Widget on grok.com
    function createStatusWidget() {
        if (document.getElementById('gw-bridge-widget')) return;
        const box = document.createElement('div');
        box.id = 'gw-bridge-widget';
        box.style.cssText = [
            'position:fixed',
            'bottom:18px',
            'right:18px',
            'z-index:999999',
            'background:rgba(15, 23, 42, 0.94)',
            'color:#e2e8f0',
            'border:1px solid #38bdf8',
            'border-radius:12px',
            'padding:10px 14px',
            'font-family:system-ui,-apple-system,sans-serif',
            'font-size:12px',
            'box-shadow:0 8px 24px rgba(0,0,0,0.45)',
            'display:flex',
            'align-items:center',
            'gap:10px',
            'backdrop-filter:blur(8px)',
        ].join(';');

        const dot = document.createElement('span');
        dot.id = 'gw-bridge-dot';
        dot.style.cssText = 'width:10px;height:10px;border-radius:50%;background:#f59e0b;display:inline-block;';

        const label = document.createElement('span');
        label.id = 'gw-bridge-label';
        label.textContent = `GhostWriter Bridge (:${bridgePort})`;

        const toggleBtn = document.createElement('button');
        toggleBtn.textContent = 'Pause';
        toggleBtn.style.cssText = [
            'background:#1e293b',
            'color:#94a3b8',
            'border:1px solid #475569',
            'border-radius:6px',
            'padding:3px 8px',
            'cursor:pointer',
            'font-size:11px',
        ].join(';');
        toggleBtn.onclick = () => {
            isPaused = !isPaused;
            toggleBtn.textContent = isPaused ? 'Resume' : 'Pause';
            updateStatus(isPaused ? 'Paused' : 'Menunggu Prompt...', isPaused ? '#64748b' : '#22c55e');
        };

        const forceBtn = document.createElement('button');
        forceBtn.id = 'gw-force-send-btn';
        forceBtn.textContent = 'Kirim Sekarang';
        forceBtn.style.cssText = [
            'background:#0284c7',
            'color:#ffffff',
            'border:1px solid #38bdf8',
            'border-radius:6px',
            'padding:3px 8px',
            'cursor:pointer',
            'font-size:11px',
            'display:none',
        ].join(';');
        forceBtn.onclick = () => {
            forceSendRequested = true;
            updateStatus('Mengambil jawaban terakhir...', '#38bdf8');
        };

        box.appendChild(dot);
        box.appendChild(label);
        box.appendChild(forceBtn);

        if (window.location.hostname.includes('openrouter.ai')) {
            const switchBtn = document.createElement('button');
            const isSao = window.location.href.includes('sao10k');
            switchBtn.textContent = isSao ? 'P1: Nous' : 'P2: Sao10k';
            switchBtn.style.cssText = [
                'background:#312e81',
                'color:#e0e7ff',
                'border:1px solid #6366f1',
                'border-radius:6px',
                'padding:3px 8px',
                'cursor:pointer',
                'font-size:11px',
            ].join(';');
            switchBtn.onclick = () => {
                const targetModel = isSao
                    ? 'nousresearch/hermes-4-405b'
                    : 'sao10k/l3.1-euryale-70b';
                window.location.href = `https://openrouter.ai/chat?models=${encodeURIComponent(targetModel)}`;
            };
            box.appendChild(switchBtn);
        }

        box.appendChild(toggleBtn);
        document.body.appendChild(box);
    }

    function updateStatus(text, color = '#22c55e') {
        createStatusWidget();
        const dot = document.getElementById('gw-bridge-dot');
        const label = document.getElementById('gw-bridge-label');
        const forceBtn = document.getElementById('gw-force-send-btn');
        if (dot) dot.style.background = color;
        if (label) label.textContent = `👻 ${text}`;
        if (forceBtn) forceBtn.style.display = isBusy ? 'inline-block' : 'none';
    }

    // Locate Grok chat input element (supports both grok.com and x.com/i/grok)
    function findChatInput() {
        const selectors = [
            'textarea[aria-label]',
            'textarea[placeholder]',
            'form textarea',
            'textarea',
            'div[contenteditable="true"][role="textbox"]',
            'div.ProseMirror[contenteditable="true"]',
            'div[contenteditable="true"]',
        ];
        for (const sel of selectors) {
            const els = Array.from(document.querySelectorAll(sel));
            for (const el of els) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 100 && rect.height > 20 && !el.disabled && !el.readOnly) {
                    return el;
                }
            }
        }
        return null;
    }

    // Locate Send button or submit trigger
    function findSendButton() {
        const btnSelectors = [
            'button[type="submit"]',
            'button[aria-label*="Send" i]',
            'button[aria-label*="Kirim" i]',
            'button[aria-label*="Ask" i]',
            'button[data-testid*="send" i]',
            'button[data-testid="grok-send-button"]',
        ];
        for (const sel of btnSelectors) {
            const btns = Array.from(document.querySelectorAll(sel));
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if (rect.width > 16 && rect.height > 16 && !btn.disabled) {
                    return btn;
                }
            }
        }
        return null;
    }

    // Check if Grok is currently streaming / generating
    function isGrokGenerating() {
        const stopSelectors = [
            'button[aria-label*="Stop" i]',
            'button[aria-label*="Hentikan" i]',
            'button[data-testid*="stop" i]',
            'button[data-testid*="cancel" i]',
        ];
        for (const sel of stopSelectors) {
            const el = document.querySelector(sel);
            if (el && el.getBoundingClientRect().width > 10) {
                return true;
            }
        }
        return false;
    }

    // Collect all visible assistant message blocks in the conversation (filtering out user prompt echoes and outer wrappers)
    function getAssistantMessages(promptText = '') {
        const promptHead = (promptText || '').trim().slice(0, 60);
        const isEcho = (txt) => promptHead.length > 15 && txt.includes(promptHead);
        const candidates = [];

        // Prefer structured markdown/prose leaf containers first
        const proseEls = Array.from(
            document.querySelectorAll('.prose, .markdown, [class*="markdown-content" i], [data-message-author-role="assistant"]')
        ).filter((el) => !el.querySelector('.prose, [data-message-author-role="assistant"]'));

        for (const el of proseEls) {
            const txt = (el.innerText || '').trim();
            if (txt.length > 0 && !isEcho(txt)) {
                candidates.push(txt);
            }
        }
        if (candidates.length > 0) return candidates;

        // Fallback: broader message containers
        const selectors = [
            '[data-testid*="message" i]',
            '[class*="markdown" i]',
            '[class*="message-bubble" i]',
            'div[dir="auto"]',
        ];
        for (const sel of selectors) {
            const els = Array.from(document.querySelectorAll(sel));
            for (const el of els) {
                const txt = (el.innerText || '').trim();
                if (txt.length > 10 && !isEcho(txt)) {
                    candidates.push(txt);
                }
            }
            if (candidates.length > 0) break;
        }
        return candidates;
    }

    // Set text on React controlled textarea or contenteditable div
    function setInputText(inputEl, text) {
        inputEl.focus();
        if (inputEl.tagName.toLowerCase() === 'textarea' || inputEl.tagName.toLowerCase() === 'input') {
            const nativeSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                'value'
            )?.set;
            if (nativeSetter) {
                nativeSetter.call(inputEl, text);
            } else {
                inputEl.value = text;
            }
            inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            inputEl.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
            // contenteditable / ProseMirror
            inputEl.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, text);
            if ((inputEl.innerText || '').trim().length < 5) {
                inputEl.textContent = text;
                inputEl.dispatchEvent(new InputEvent('input', { bubbles: true, data: text }));
            }
        }
    }

    async function sleep(ms) {
        return new Promise((r) => setTimeout(r, ms));
    }

    async function submitPrompt(inputEl) {
        for (let attempt = 0; attempt < 4; attempt++) {
            const sendBtn = findSendButton();
            if (sendBtn) {
                sendBtn.click();
            } else {
                const form = inputEl.closest('form');
                if (form && typeof form.requestSubmit === 'function') {
                    form.requestSubmit();
                } else {
                    inputEl.dispatchEvent(
                        new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true,
                        })
                    );
                }
            }
            await sleep(500);
            const remaining = (inputEl.value !== undefined ? inputEl.value : inputEl.innerText) || '';
            if (remaining.trim().length === 0) {
                return true;
            }
        }
        return false;
    }

    async function tryStartNewChatIfNeeded(prevMsgCount) {
        const bodyLow = (document.body?.innerText || '').toLowerCase();
        const hasMixedErr =
            bodyLow.includes('encrypted reasoning') ||
            bodyLow.includes('start a new conversation') ||
            bodyLow.includes('maximum context length');
        if (prevMsgCount < 1 && !hasMixedErr) return false;

        const candidates = Array.from(document.querySelectorAll('button, [role="button"]'));
        for (const btn of candidates) {
            const txt = (
                btn.innerText ||
                btn.getAttribute('aria-label') ||
                btn.getAttribute('title') ||
                btn.getAttribute('data-testid') ||
                ''
            ).trim().toLowerCase();
            if (
                txt === 'new chat' ||
                txt === 'new' ||
                txt.includes('new chat') ||
                txt.includes('new-chat') ||
                txt.includes('obrolan baru')
            ) {
                const rect = btn.getBoundingClientRect();
                if (rect.width > 10 && rect.height > 10 && !btn.disabled) {
                    btn.click();
                    await sleep(900);
                    return true;
                }
            }
        }
        return false;
    }

    function isProviderErrorText(text) {
        const low = (text || '').toLowerCase();
        return (
            low.includes('invalid request:') ||
            low.includes('maximum context length') ||
            low.includes('please reduce the length of the input prompt') ||
            low.includes('encrypted reasoning') ||
            low.includes('mixed history') ||
            low.includes('start a new conversation')
        );
    }

    async function executeTask(task) {
        isBusy = true;
        forceSendRequested = false;
        currentTaskId = task.id;
        updateStatus(`Menulis Prompt #${task.id.slice(0, 6)}...`, '#38bdf8');

        try {
            let beforeMessages = getAssistantMessages(task.prompt);
            // Reset to a fresh chat thread if old history exists so 131k context never overflows
            if (await tryStartNewChatIfNeeded(beforeMessages.length)) {
                beforeMessages = getAssistantMessages(task.prompt);
            }

            const inputEl = findChatInput();
            if (!inputEl) {
                throw new Error('Kotak input chat tidak ditemukan. Pastikan Anda sudah login di halaman chat.');
            }

            const prevCount = beforeMessages.length;
            const prevLastText = prevCount > 0 ? beforeMessages[prevCount - 1] : '';

            setInputText(inputEl, task.prompt);
            await sleep(400);
            await submitPrompt(inputEl);

            updateStatus('Menunggu Grok selesai menjawab...', '#a855f7');

            // Wait for response to start & stabilize, sending heartbeats every 8s
            let started = false;
            let lastSeenText = '';
            let stableTicks = 0;
            let lastHeartbeat = Date.now();
            const maxWaitMs = 720000; // 12 minutes max for long chapter generation
            const startTime = Date.now();

            await sleep(1500);

            while (Date.now() - startTime < maxWaitMs) {
                await sleep(1000);

                if (Date.now() - lastHeartbeat >= 8000) {
                    lastHeartbeat = Date.now();
                    bridgeRequest('POST', '/heartbeat', { id: task.id }).catch(() => {});
                }

                const generating = isGrokGenerating();
                const currentMessages = getAssistantMessages(task.prompt);
                const currCount = currentMessages.length;
                const latestText = currCount > 0 ? currentMessages[currCount - 1] : '';

                const isNewOrUpdated =
                    currCount > prevCount ||
                    (latestText && latestText !== prevLastText);

                if (generating || isNewOrUpdated) {
                    started = true;
                }

                if (started && latestText && latestText !== prevLastText) {
                    if (latestText === lastSeenText && !generating) {
                        stableTicks += 1;
                    } else {
                        stableTicks = 0;
                        lastSeenText = latestText;
                    }

                    updateStatus(`Menerima (${lastSeenText.length} huruf)...`, '#a855f7');

                    if (stableTicks >= 6 && lastSeenText.trim().length > 0) {
                        break;
                    }
                }

                if (forceSendRequested) {
                    const fallbackText = latestText || lastSeenText;
                    if (fallbackText && fallbackText.trim().length > 0) {
                        lastSeenText = fallbackText;
                        break;
                    }
                    forceSendRequested = false;
                }
            }

            if (!lastSeenText || lastSeenText.trim().length === 0) {
                throw new Error('Waktu tunggu habis atau teks balasan AI tidak terdeteksi di halaman.');
            }
            if (isProviderErrorText(lastSeenText)) {
                throw new Error(`Model menolak karena batas konteks/request: ${lastSeenText.slice(0, 180)}`);
            }

            await bridgeRequest('POST', '/result', {
                id: task.id,
                content: lastSeenText.trim(),
            });

            isBusy = false;
            forceSendRequested = false;
            updateStatus('Selesai! Menunggu tugas berikutnya...', '#22c55e');
        } catch (err) {
            isBusy = false;
            forceSendRequested = false;
            updateStatus(`Kendala: ${err.message}`, '#ef4444');
            try {
                await bridgeRequest('POST', '/result', {
                    id: task.id,
                    error: err.message || String(err),
                });
            } catch (_) {}
        } finally {
            isBusy = false;
            forceSendRequested = false;
            currentTaskId = null;
        }
    }

    async function pollLoop() {
        createStatusWidget();
        while (true) {
            if (!isPaused && !isBusy) {
                try {
                    const data = await bridgeRequest('GET', '/poll');
                    if (data && data.task && data.task.id) {
                        await executeTask(data.task);
                    } else {
                        updateStatus('Terhubung ke GhostWriter (Siap)', '#22c55e');
                    }
                } catch (_) {
                    updateStatus(`Menunggu GhostWriter (:${bridgePort})`, '#f59e0b');
                }
            }
            await sleep(1500);
        }
    }

    setTimeout(pollLoop, 1500);
})();
