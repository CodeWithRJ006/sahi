"""HTML UI template for SAHI Live Voice & Payment Safety Demonstration."""

LIVE_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SAHI Live — Indic Voice Payment Safety Benchmark & Deterministic Guard</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f2937;
      --text: #f9fafb;
      --text-muted: #9ca3af;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --green: #10b981;
      --green-bg: #064e3b;
      --amber: #f59e0b;
      --amber-bg: #78350f;
      --red: #ef4444;
      --red-bg: #7f1d1d;
      --blue: #3b82f6;
      --blue-bg: #1e3a8a;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px 16px;
    }
    .container { max-width: 1100px; margin: 0 auto; }
    header {
      text-align: center;
      margin-bottom: 24px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
    }
    .badge-sim {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      background: var(--amber-bg);
      color: var(--amber);
      margin-bottom: 8px;
    }
    h1 { font-size: 2rem; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.025em; }
    .subtitle { color: var(--text-muted); font-size: 1rem; max-width: 700px; margin: 0 auto; }

    .grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 20px; margin-bottom: 24px; }
    @media (max-width: 850px) { .grid { grid-template-columns: 1fr; } }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .card-title {
      font-size: 1.1rem;
      font-weight: 700;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* Balance bar */
    .balance-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #1f2937;
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }
    .balance-label { font-size: 0.85rem; color: var(--text-muted); }
    .balance-val { font-size: 1.35rem; font-weight: 800; color: var(--green); }

    /* Preset buttons */
    .presets-label { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; font-weight: 700; }
    .preset-group { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
    .btn-preset {
      background: #1f2937;
      color: var(--text);
      border: 1px solid #374151;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-preset:hover { background: #374151; border-color: var(--accent); }

    /* Voice Controls */
    .voice-control-box {
      text-align: center;
      padding: 24px 16px;
      border: 2px dashed #374151;
      border-radius: 10px;
      margin-bottom: 16px;
    }
    .btn-mic {
      background: #ef4444;
      color: white;
      border: none;
      width: 64px;
      height: 64px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 1.5rem;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
      transition: transform 0.2s, background 0.2s;
    }
    .btn-mic:hover { transform: scale(1.05); }
    .btn-mic.recording {
      background: #b91c1c;
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
      70% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }
      100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .mic-status { margin-top: 10px; font-size: 0.85rem; color: var(--text-muted); }

    /* Text input row */
    .input-row { display: flex; gap: 8px; margin-bottom: 12px; }
    input[type="text"], select {
      flex: 1;
      background: #1f2937;
      border: 1px solid #374151;
      color: var(--text);
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 0.95rem;
    }
    input[type="text"]:focus, select:focus { outline: none; border-color: var(--accent); }
    .btn-primary {
      background: var(--accent);
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-primary:hover { background: var(--accent-hover); }

    /* Decision Panel */
    .decision-badge {
      display: inline-block;
      padding: 6px 16px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 1.25rem;
      letter-spacing: 0.05em;
      margin-bottom: 12px;
    }
    .action-EXECUTE { background: var(--green-bg); color: var(--green); border: 1px solid var(--green); }
    .action-READ_BACK { background: var(--blue-bg); color: var(--blue); border: 1px solid var(--blue); }
    .action-RE_ASK { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber); }
    .action-ESCALATE { background: var(--red-bg); color: var(--red); border: 1px solid var(--red); }

    .meta-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    .meta-table td { padding: 6px 8px; border-bottom: 1px solid #1f2937; font-size: 0.88rem; }
    .meta-table td:first-child { color: var(--text-muted); width: 40%; font-weight: 600; }

    .explanation-box {
      background: #1f2937;
      padding: 12px;
      border-radius: 6px;
      margin-top: 12px;
      font-size: 0.88rem;
      border-left: 4px solid var(--accent);
    }

    /* Confirmation Dialog */
    .confirmation-box {
      margin-top: 16px;
      padding: 16px;
      border-radius: 8px;
      background: #1e3a8a;
      border: 1px solid var(--accent);
      text-align: center;
    }
    .btn-confirm {
      background: var(--green);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-weight: 700;
      cursor: pointer;
      margin-right: 8px;
      font-size: 0.95rem;
    }
    .btn-cancel {
      background: #4b5563;
      color: white;
      border: none;
      padding: 10px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.95rem;
    }

    /* Ledger Table */
    .ledger-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    .ledger-table th { background: #1f2937; padding: 8px; text-align: left; font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; }
    .ledger-table td { padding: 8px; border-bottom: 1px solid #1f2937; font-size: 0.85rem; }
  </style>
</head>
<body>
<div class="container">
  <header>
    <div class="badge-sim">Simulation Only — Synthetic Bank Ledger</div>
    <h1>🛡️ SAHI Live Voice & Safety Guard</h1>
    <p class="subtitle">Multilingual Indic amount safety benchmark & deterministic consensus guard. Test voice or text payment instructions and watch the safety layer catch mismatches before execution.</p>
  </header>

  <div class="grid">
    <!-- LEFT PANEL: Inputs & Voice -->
    <div class="card">
      <div class="card-title">
        <span>Payment Instruction</span>
        <span style="font-size: 0.8rem; font-weight: normal; color: var(--text-muted)">Hindi • Telugu • Hinglish • English</span>
      </div>

      <!-- Account & Recipient -->
      <div class="balance-bar">
        <div>
          <div class="balance-label">From Account</div>
          <div style="font-weight: 700;">ACC_USER_001 (Primary Test User)</div>
        </div>
        <div style="text-align: right;">
          <div class="balance-label">Simulated Balance</div>
          <div class="balance-val" id="accBalance">₹100,000</div>
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <label class="presets-label">Select Simulated Payee</label>
        <select id="payeeSelect">
          <option value="ramesh@upi">ramesh@upi (ACC_RAMESH_002)</option>
          <option value="suresh@upi">suresh@upi (ACC_SURESH_003)</option>
          <option value="custom">Custom UPI ID...</option>
        </select>
        <input type="text" id="customPayee" placeholder="e.g. merchant@icici" style="display:none; margin-top:8px;">
      </div>

      <!-- Preset Scenarios -->
      <div class="presets-label">Click Preset Test Scenarios</div>
      <div class="preset-group">
        <button class="btn-preset" onclick="loadPreset('A')">🟢 Scenario A: ₹2500 भेजो (Agreement)</button>
        <button class="btn-preset" onclick="loadPreset('B')">🔴 Scenario B: ₹5000 vs ₹50,000 (10× Mismatch)</button>
        <button class="btn-preset" onclick="loadPreset('C')">🟠 Scenario C: send 500 no wait 5000 (Ambiguous)</button>
        <button class="btn-preset" onclick="loadPreset('D')">🟢 Scenario D: five hundred rupees no wait six hundred</button>
        <button class="btn-preset" onclick="loadPreset('E')">🔴 Scenario E: send 50 karod (Ceiling Violation)</button>
      </div>

      <!-- Microphone Push-To-Talk -->
      <div class="voice-control-box">
        <button id="btnMic" class="btn-mic" onclick="toggleRecording()">🎙️</button>
        <div id="micStatus" class="mic-status">Click to speak using your microphone (or type below)</div>
      </div>

      <!-- Direct Text Form -->
      <div class="input-row">
        <input type="text" id="txtInput" placeholder="Or type instruction (e.g. ₹2500 भेजो or రెండు వేల రూపాయలు)..." onkeydown="if(event.key==='Enter') submitUtterance()">
        <button class="btn-primary" onclick="submitUtterance()">Analyze</button>
      </div>

      <div id="proposalOverrideRow" style="display:none; margin-top: 12px; background: #1f2937; padding: 10px; border-radius: 6px;">
        <span style="font-size: 0.8rem; color: var(--amber); font-weight: 600;">Simulated Agent Proposal (Override): </span>
        <input type="number" id="overrideProposal" placeholder="e.g. 50000" style="padding: 4px 8px; width: 120px;">
        <button style="padding: 4px 8px; cursor: pointer;" onclick="clearOverride()">Clear</button>
      </div>
    </div>

    <!-- RIGHT PANEL: Deterministic Guard Analysis -->
    <div class="card">
      <div class="card-title">
        <span>SahiGuard Safety Decision</span>
        <span id="riskBadge" style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: #374151;">IDLE</span>
      </div>

      <div id="decisionArea" style="text-align: center; padding: 16px 0;">
        <div id="decisionBadge" class="decision-badge" style="background:#1f2937; color:var(--text-muted)">AWAITING INPUT</div>
      </div>

      <table class="meta-table">
        <tr><td>Spoken / Transcript</td><td id="resTranscript">—</td></tr>
        <tr><td>Parsed Amount</td><td id="resParsedAmount">—</td></tr>
        <tr><td>Parse Status</td><td id="resParseStatus">—</td></tr>
        <tr><td>Guard Reason Code</td><td id="resReasonCode">—</td></tr>
        <tr><td>Candidate Figures</td><td id="resCandidates">—</td></tr>
      </table>

      <div id="explanationBox" class="explanation-box" style="display:none;">
        <div style="font-weight:700; margin-bottom:4px;">Safety Explanation:</div>
        <div id="resExplanation"></div>
      </div>

      <!-- Confirmation Flow Area -->
      <div id="confirmationBox" class="confirmation-box" style="display:none;">
        <div style="font-weight: 700; margin-bottom: 8px;">Action Permitted by Guard</div>
        <div id="confirmPromptText" style="font-size: 0.9rem; margin-bottom: 12px;"></div>
        <button class="btn-confirm" onclick="confirmTransfer()">✅ Confirm Payment</button>
        <button class="btn-cancel" onclick="cancelTransfer()">Cancel</button>
      </div>
    </div>
  </div>

  <!-- BOTTOM: Audit Ledger History -->
  <div class="card">
    <div class="card-title">
      <span>Simulated Mock Bank Ledger (Audit Trail)</span>
      <button class="btn-preset" onclick="refreshLedger()">🔄 Refresh</button>
    </div>
    <div style="overflow-x: auto;">
      <table class="ledger-table">
        <thead>
          <tr>
            <th>Tx ID</th>
            <th>From</th>
            <th>To Payee</th>
            <th>Amount (INR)</th>
            <th>Guard Reason</th>
            <th>Timestamp</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="ledgerBody">
          <tr><td colspan="7" style="text-align:center; color:var(--text-muted)">No transactions yet in current session.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
  let pendingData = null;
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  document.getElementById('payeeSelect').addEventListener('change', function() {
    document.getElementById('customPayee').style.display = this.value === 'custom' ? 'block' : 'none';
  });

  function getSelectedPayee() {
    const sel = document.getElementById('payeeSelect').value;
    if (sel === 'custom') {
      return document.getElementById('customPayee').value.trim() || 'custom@upi';
    }
    return sel;
  }

  function loadPreset(key) {
    const input = document.getElementById('txtInput');
    const override = document.getElementById('overrideProposal');
    const overrideRow = document.getElementById('proposalOverrideRow');

    if (key === 'A') {
      input.value = "₹2500 भेजो";
      override.value = "";
      overrideRow.style.display = "none";
    } else if (key === 'B') {
      input.value = "₹5000 పంపించు";
      override.value = "50000";
      overrideRow.style.display = "block";
    } else if (key === 'C') {
      input.value = "send 500 no wait 5000";
      override.value = "";
      overrideRow.style.display = "none";
    } else if (key === 'D') {
      input.value = "five hundred rupees no wait six hundred rupees";
      override.value = "";
      overrideRow.style.display = "none";
    } else if (key === 'E') {
      input.value = "send 50 karod";
      override.value = "";
      overrideRow.style.display = "none";
    }
    submitUtterance();
  }

  function clearOverride() {
    document.getElementById('overrideProposal').value = "";
    document.getElementById('proposalOverrideRow').style.display = "none";
  }

  async function submitUtterance() {
    const text = document.getElementById('txtInput').value.trim();
    if (!text) return;
    const payee = getSelectedPayee();
    const overrideVal = document.getElementById('overrideProposal').value;
    const agentProposal = overrideVal ? parseInt(overrideVal, 10) : null;

    document.getElementById('decisionBadge').innerText = "ANALYZING...";
    document.getElementById('decisionBadge').className = "decision-badge";

    try {
      const resp = await fetch('/api/voice/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          to_payee: payee,
          from_account: 'ACC_USER_001',
          agent_proposed_amount: agentProposal
        })
      });
      const data = await resp.json();
      renderDecision(data);
    } catch (err) {
      alert("Error processing instruction: " + err);
    }
  }

  function renderDecision(data) {
    pendingData = data;
    document.getElementById('resTranscript').innerText = data.transcript || "—";
    document.getElementById('resParsedAmount').innerText = data.parsed_amount !== null ? `₹${data.parsed_amount.toLocaleString()}` : "None";
    document.getElementById('resParseStatus').innerText = data.parsed_status || "—";
    document.getElementById('resReasonCode').innerText = data.reason_code || "—";
    document.getElementById('resCandidates').innerText = (data.candidates && data.candidates.length) ? data.candidates.map(c => `₹${c}`).join(", ") : "None";

    const badge = document.getElementById('decisionBadge');
    badge.innerText = data.guard_action;
    badge.className = `decision-badge action-${data.guard_action}`;

    const risk = document.getElementById('riskBadge');
    risk.innerText = `RISK: ${data.risk_level}`;
    risk.style.background = data.risk_level === 'CRITICAL' ? 'var(--red-bg)' : data.risk_level === 'HIGH' ? 'var(--amber-bg)' : 'var(--green-bg)';

    const expBox = document.getElementById('explanationBox');
    expBox.style.display = 'block';
    document.getElementById('resExplanation').innerText = data.explanation;

    // Spoken voice playback via Web Speech API if audio is absent
    if (data.spoken_response) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(data.spoken_response);
        window.speechSynthesis.speak(utter);
      }
    }

    const confirmBox = document.getElementById('confirmationBox');
    if (data.can_confirm && data.pending_transfer) {
      confirmBox.style.display = 'block';
      document.getElementById('confirmPromptText').innerText =
        `Authorise debit of ₹${data.pending_transfer.amount_inr.toLocaleString()} from ACC_USER_001 to ${data.pending_transfer.to_payee}?`;
    } else {
      confirmBox.style.display = 'none';
    }
  }

  async function confirmTransfer() {
    if (!pendingData || !pendingData.pending_transfer) return;
    const t = pendingData.pending_transfer;
    try {
      const resp = await fetch('/api/voice/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_account: t.from_account,
          to_payee: t.to_payee,
          proposed_amount: t.amount_inr,
          confirmed_amount: t.amount_inr,
          confirmed_payee: t.to_payee,
          is_confirmed: true
        })
      });
      const res = await resp.json();
      if (res.success) {
        alert(`✅ Payment Executed! Transaction ID: ${res.transaction_id}`);
        document.getElementById('confirmationBox').style.display = 'none';
        refreshBalance();
        refreshLedger();
      } else {
        alert(`❌ Confirmation Blocked: ${res.message || res.status}`);
      }
    } catch (err) {
      alert("Execution error: " + err);
    }
  }

  function cancelTransfer() {
    document.getElementById('confirmationBox').style.display = 'none';
    pendingData = null;
  }

  async function refreshBalance() {
    try {
      const res = await fetch('/accounts/ACC_USER_001');
      const d = await res.json();
      document.getElementById('accBalance').innerText = `₹${d.balance_inr.toLocaleString()}`;
    } catch (e) {}
  }

  async function refreshLedger() {
    try {
      const res = await fetch('/transactions?limit=15');
      const list = await res.json();
      const body = document.getElementById('ledgerBody');
      if (!list || list.length === 0) {
        body.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted)">No transactions recorded yet.</td></tr>';
        return;
      }
      body.innerHTML = list.map(tx => {
        let guardReason = "—";
        try {
          const gd = JSON.parse(tx.guard_decision_json || "{}");
          guardReason = gd.reason_code || "—";
        } catch(e) {}
        return `<tr>
          <td><code style="font-size:0.78rem;">${tx.transaction_id}</code></td>
          <td>${tx.from_account}</td>
          <td><b>${tx.to_payee}</b></td>
          <td style="color:var(--green); font-weight:700;">₹${tx.amount_inr.toLocaleString()}</td>
          <td><span style="font-size:0.75rem; background:#1f2937; padding:2px 6px; border-radius:4px;">${guardReason}</span></td>
          <td style="font-size:0.78rem; color:var(--text-muted);">${tx.created_at.substring(0, 19).replace('T', ' ')}</td>
          <td><b style="color:var(--green); font-size:0.8rem;">${tx.status}</b></td>
        </tr>`;
      }).join('');
    } catch (e) {}
  }

  // Audio Recording (Push-to-Talk)
  async function toggleRecording() {
    const btn = document.getElementById('btnMic');
    const status = document.getElementById('micStatus');

    if (!isRecording) {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Microphone recording is not supported in this browser environment. You can use direct text or preset buttons.");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = handleAudioUpload;
        mediaRecorder.start();
        isRecording = true;
        btn.classList.add('recording');
        status.innerText = "🔴 Listening... Speak your amount in Hindi, Telugu, Hinglish or English (Click mic again to stop).";
      } catch (err) {
        alert("Could not access microphone: " + err.message);
      }
    } else {
      mediaRecorder.stop();
      isRecording = false;
      btn.classList.remove('recording');
      status.innerText = "Processing recorded audio...";
    }
  }

  async function handleAudioUpload() {
    const status = document.getElementById('micStatus');
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const reader = new FileReader();
    reader.readAsDataURL(audioBlob);
    reader.onloadend = async function() {
      const base64Audio = reader.result;
      status.innerText = "Sending audio to SAHI safety pipeline...";
      try {
        const resp = await fetch('/api/voice/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            audio_base64: base64Audio,
            to_payee: getSelectedPayee(),
            from_account: 'ACC_USER_001'
          })
        });
        const data = await resp.json();
        renderDecision(data);
        status.innerText = "Click mic to speak again.";
      } catch (err) {
        status.innerText = "Audio processing error.";
        alert("Audio error: " + err);
      }
    };
  }

  // Initial load
  refreshBalance();
  refreshLedger();
</script>
</body>
</html>
"""
