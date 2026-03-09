<script lang="ts">
  import { wsUnity } from '$lib/appState.svelte';

  let mode = $state<'raw' | 'legacy'>('raw');
  let eventName = $state('');
  let jsonPayload = $state('{}');
  let error = $state('');

  function send() {
    error = '';
    let payload: object;
    try {
      payload = JSON.parse(jsonPayload);
    } catch (e) {
      error = `Invalid JSON: ${e}`;
      return;
    }
    if (!eventName.trim()) {
      error = 'Event name is required';
      return;
    }
    if (mode === 'raw') {
      wsUnity.send(eventName.trim(), payload as Record<string, unknown>);
    } else {
      wsUnity.sendLegacy(eventName.trim(), payload);
    }
  }
</script>

<section class="panel">
  <h3>Raw / Legacy Send</h3>

  <div class="mode-toggle">
    <button class:active={mode === 'raw'} onclick={() => (mode = 'raw')}>Raw</button>
    <button class:active={mode === 'legacy'} onclick={() => (mode = 'legacy')}>Legacy</button>
  </div>

  <label class="field">
    <span>Event / Type</span>
    <input type="text" bind:value={eventName} placeholder="e.g. pc_debug_calibration_request" />
  </label>

  <label class="field">
    <span>Payload (JSON)</span>
    <textarea rows="4" bind:value={jsonPayload}></textarea>
  </label>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <button class="btn" onclick={send}>Send</button>
</section>

<style>
  .panel {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
  }
  h3 {
    margin: 0 0 12px;
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .mode-toggle {
    display: flex;
    gap: 4px;
    margin-bottom: 12px;
  }
  .mode-toggle button {
    flex: 1;
    padding: 6px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #94a3b8;
    font-size: 0.8rem;
    cursor: pointer;
  }
  .mode-toggle button.active {
    background: #1e3a5f;
    color: #38bdf8;
    border-color: #38bdf8;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 10px;
  }
  .field span {
    font-size: 0.75rem;
    color: #94a3b8;
  }
  input, textarea {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #e2e8f0;
    padding: 8px;
    font-family: monospace;
    font-size: 0.8rem;
    resize: vertical;
  }
  input:focus, textarea:focus {
    outline: none;
    border-color: #38bdf8;
  }
  .error {
    color: #f87171;
    font-size: 0.8rem;
    margin: 0 0 8px;
  }
  .btn {
    padding: 8px 24px;
    border: 1px solid #334155;
    border-radius: 6px;
    background: #1e3a5f;
    color: #38bdf8;
    font-size: 0.8rem;
    cursor: pointer;
  }
  .btn:hover {
    background: #2563eb;
    color: #fff;
  }
</style>
