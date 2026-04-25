# Day Recap — Reply-to-Question Feature Plan

## Goal
Let the user respond (text or voice) to the reflective question on the **active** report card in the Day Recap scroll wheel. Replies are stored per-timestamp, persist across sessions, and give the card a subtle "answered" indicator.

## Current state (what exists)
- `REPORTS` array in [ui_mockup.html:2253](ui_mockup.html#L2253): each entry has `t`, `state`, `text`, `question`.
- Each report renders a `.dr-report` card with `.r-time`, `.r-text`, `.r-question` ([ui_mockup.html:2384](ui_mockup.html#L2384)).
- `.r-question` is collapsed (`max-height: 0`) and only expands on `.is-active`.
- The Daily Review v2 already has `mockMic()` ([ui_mockup.html:2218](ui_mockup.html#L2218)) — a working mock that types an answer after 1 s with a GSAP button bounce.

## Design principles
1. **Don't disrupt the scroll-wheel feel.** Reply UI lives *inside* the active card only. Inactive/near cards stay slim.
2. **Optional, never required.** No "submit to continue" gates. Scrolling away auto-saves.
3. **Tactile, calm input.** Textarea + mic button side-by-side, submit on Enter or blur.
4. **Visible memory.** Answered card shows a small glowing dot (tinted to its state color).

---

## UX flow

```
[scroll]  →  card becomes active  →  question expands  →
reply block fades in (200ms delay)  →
user types OR clicks 🎙  →  mock answer types in char-by-char  →
blur / Enter / scroll away  →  auto-saved, answered dot appears
```

---

## Mock voice behaviour (demo)
Each `REPORT` entry has a `mockAnswer` string. When the mic button is clicked:
1. Button pulses (GSAP bounce) and enters `.listening` state.
2. After **800 ms** (simulated "listening"), the answer types into the textarea **character by character** at ~40 ms/char.
3. Button returns to idle. Reply is auto-committed.

`mockAnswer` strings are contextual per question (not a single hardcoded phrase).

---

## DOM additions

Inside `_renderReports()` template:

```html
<article class="dr-report" data-idx="${i}" style="--r-tint:${tint}; --r-bg:${bg}">
    <div class="r-time">${r.t}</div>
    <div class="r-text">${r.text}</div>
    <div class="r-question">${r.question}</div>
    <div class="r-reply">
        <div class="r-reply-row">
            <textarea class="r-reply-input" rows="1"
                      placeholder="Type or speak your reflection…"
                      aria-label="Your reply"></textarea>
            <button class="r-mic-btn" aria-label="Dictate reply">
                <svg viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>
            </button>
        </div>
    </div>
    <div class="r-answered-dot" aria-label="Answered"></div>
</article>
```

---

## CSS additions

```css
/* Reply block */
.dr-report .r-reply { max-height:0; overflow:hidden; opacity:0; margin-top:0;
    transform:translateY(8px);
    transition: max-height .5s cubic-bezier(.4,0,.2,1) .25s,
                opacity .4s ease .3s, margin-top .4s ease .25s,
                transform .45s cubic-bezier(.34,1.56,.64,1) .25s; }
.dr-report.is-active .r-reply { max-height:8rem; opacity:1; margin-top:.6rem; transform:translateY(0); }

.r-reply-row { display:flex; gap:.5rem; align-items:flex-start; }

.r-reply-input { flex:1; min-height:38px; background:rgba(0,0,0,.22);
    border:1px solid rgba(255,255,255,.18); border-radius:10px; color:#fff;
    font-family:'DM Sans',sans-serif; font-size:1rem; padding:.55rem .7rem;
    resize:none; line-height:1.4; transition:border-color .25s,background .25s; }
.r-reply-input:focus { outline:none;
    border-color:rgba(var(--r-tint,74,200,255),.7); background:rgba(0,0,0,.32); }
.r-reply-input.has-saved { font-family:'Fraunces',serif; font-style:italic;
    color:rgba(255,255,255,.92); }

.r-mic-btn { flex-shrink:0; width:38px; height:38px; border-radius:50%;
    background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.18);
    color:#fff; cursor:pointer; display:flex; align-items:center;
    justify-content:center; transition:background .2s,border-color .2s; }
.r-mic-btn svg { width:18px; height:18px; fill:currentColor; }
.r-mic-btn:hover { background:rgba(255,255,255,.15); }
.r-mic-btn.listening { background:rgba(255,120,90,.3);
    border-color:rgba(255,150,110,.6);
    animation:dr-mic-pulse 1.2s ease-in-out infinite; }
@keyframes dr-mic-pulse {
    0%,100% { box-shadow:0 0 0 0 rgba(255,120,90,.5); }
    50%     { box-shadow:0 0 0 6px rgba(255,120,90,0); } }

.r-answered-dot { position:absolute; top:.7rem; right:.8rem;
    width:7px; height:7px; border-radius:50%;
    background:rgba(var(--r-tint,74,200,255),.9);
    box-shadow:0 0 8px rgba(var(--r-tint,74,200,255),.7);
    opacity:0; transition:opacity .4s ease; }
.dr-report.is-answered .r-answered-dot { opacity:1; }
```

---

## JS additions

### Storage
```js
const STORAGE_KEY = 'dayRecap.replies.v1';
let _replies = {};
function _loadReplies() { try { _replies = JSON.parse(localStorage.getItem(STORAGE_KEY)||'{}'); } catch{} }
function _saveReplies() { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(_replies)); } catch{} }
function _setReply(time, text) {
    const t = (text||'').trim();
    if (t) _replies[time] = t; else delete _replies[time];
    _saveReplies();
}
```

### Mock voice
```js
function _mockVoice(btn, input, answer) {
    btn.classList.add('listening');
    gsap.to(btn, { scale:1.2, duration:0.12, yoyo:true, repeat:3 });
    setTimeout(() => {
        btn.classList.remove('listening');
        input.value = '';
        let i = 0;
        const tick = setInterval(() => {
            input.value += answer[i++];
            input.style.height = 'auto';
            input.style.height = input.scrollHeight + 'px';
            if (i >= answer.length) { clearInterval(tick); _commitReply(input); }
        }, 40);
    }, 800);
}
```

### `_bindReplies()`
```js
function _bindReplies() {
    els.reportsList.addEventListener('input', e => {
        if (!e.target.matches('.r-reply-input')) return;
        e.target.style.height = 'auto';
        e.target.style.height = e.target.scrollHeight + 'px';
    });
    els.reportsList.addEventListener('keydown', e => {
        if (!e.target.matches('.r-reply-input')) return;
        e.stopPropagation();  // don't hijack scrubber keys
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); _commitReply(e.target); }
    });
    els.reportsList.addEventListener('focusin', e => {
        if (!e.target.matches('.r-reply-input')) return;
        if (_playbackTween) { _playbackTween.kill(); _playbackTween = null;
            els.playbackBtn.classList.remove('playing'); els.playbackLbl.textContent = 'Your day playback'; }
    });
    els.reportsList.addEventListener('blur', e => {
        if (e.target.matches('.r-reply-input')) _commitReply(e.target);
    }, true);
    els.reportsList.addEventListener('click', e => {
        if (!e.target.closest('.r-mic-btn')) return;
        const card = e.target.closest('.dr-report');
        const idx  = +card.dataset.idx;
        const input = card.querySelector('.r-reply-input');
        _mockVoice(e.target.closest('.r-mic-btn'), input, REPORTS[idx].mockAnswer);
    });
}
```

### `_commitReply(input)`
```js
function _commitReply(input) {
    const card = input.closest('.dr-report');
    const time = REPORTS[+card.dataset.idx].t;
    _setReply(time, input.value);
    if (input.value.trim()) {
        card.classList.add('is-answered');
        input.classList.add('has-saved');
    } else {
        card.classList.remove('is-answered');
        input.classList.remove('has-saved');
    }
}
```

### Guard drag handler
In `_bindReportsDrag` `onDown`:
```js
if (e.target.closest('.r-reply')) return;
```

---

## REPORTS data addition
Each entry needs a `mockAnswer` field, e.g.:
```js
{ t:'08:00', state:'calm', text:'...', question:'What set the tone today?',
  mockAnswer:'The quiet before anyone else woke up.' },
```

---

## Edge cases

| Case | Behavior |
|---|---|
| Scroll away without saving | `blur` event auto-commits |
| Clear reply + blur | Removes from storage, dot fades |
| Reload | `_loadReplies()` restores values and `is-answered` on render |
| Mic clicked mid-type | Replaces current content with mock answer |

---

## Implementation order
1. Add `mockAnswer` to every REPORT entry.
2. Storage helpers + `_loadReplies()` in `init()`.
3. Update `_renderReports()` template with reply block + answered-dot.
4. CSS block (reply, mic, answered-dot, animations).
5. `_mockVoice()` + `_commitReply()` + `_bindReplies()`.
6. Guard in `_bindReportsDrag`.
7. Call `_bindReplies()` from `init()`.
