<script lang="ts">
  import { api } from '$lib/api.svelte';
  import { appState } from '$lib/appState.svelte';
  import type { RobotStatusResponse } from '$lib/types';

  let loading = $state('');
  let statusLoading = $state(false);

  async function action(name: string, fn: () => Promise<unknown>) {
    loading = name;
    try {
      await fn();
      appState.addToast(`${name} succeeded`, 'success');
      // Refresh status after connection actions
      if (['Connect', 'Disconnect'].includes(name)) {
        await refreshStatus();
      }
    } catch (e) {
      appState.addToast(`${name} failed: ${e}`, 'error');
    } finally {
      loading = '';
    }
  }

  async function refreshStatus() {
    statusLoading = true;
    try {
      const s = await api.robotStatus();
      appState.robotStatus = s;
    } catch {
      // ignore
    } finally {
      statusLoading = false;
    }
  }

  const isConnected = $derived(appState.robotStatus?.connected ?? false);
  const mode = $derived(appState.robotStatus?.mode ?? '?');
  const isManualMode = $derived(appState.robotStatus?.manual_mode ?? false);

  async function toggleManualMode() {
    loading = 'ManualMode';
    try {
      const res = await api.robotManualMode(!isManualMode);
      if (!res.success) {
        appState.addToast(`Manual mode failed: ${res.message}`, 'error');
      }
      // status は broadcast で自動更新されるが念のため
      appState.robotStatus = await api.robotStatus();
    } catch (e) {
      appState.addToast(`Manual mode error: ${e}`, 'error');
    } finally {
      loading = '';
    }
  }
</script>

<section class="panel">
  <div class="panel-header">
    <h3>Robot Controls</h3>
    <button class="btn-sm" onclick={refreshStatus} disabled={statusLoading}>
      {statusLoading ? '…' : '↻ Status'}
    </button>
  </div>

  <div class="status-row">
    <span class="status-dot" class:connected={isConnected}></span>
    <span class="status-text">
      {isConnected ? 'Connected' : 'Disconnected'}
      <span class="mode-badge">({mode})</span>
    </span>
    {#if appState.robotStatus?.error_code}
      <span class="error-badge">Error: {appState.robotStatus.error_code}</span>
    {/if}
  </div>

  <div class="btn-group">
    {#if !isConnected}
      <button class="btn connect" disabled={loading === 'Connect'} onclick={() => action('Connect', api.robotConnect)}>
        {loading === 'Connect' ? '…' : 'Connect'}
      </button>
    {:else}
      <button class="btn disconnect" disabled={loading === 'Disconnect'} onclick={() => action('Disconnect', api.robotDisconnect)}>
        {loading === 'Disconnect' ? '…' : 'Disconnect'}
      </button>
    {/if}
    <!-- <button class="btn" disabled={loading === 'Home'} onclick={() => action('Home', api.robotHome)}>
      {loading === 'Home' ? '…' : 'Home'}
    </button> -->
    <button class="btn" disabled={loading === 'Initial'} onclick={() => action('Initial', api.robotInitial)}>
      {loading === 'Initial' ? '…' : 'Initial'}
    </button>
    <button class="btn" disabled={loading === 'Reset'} onclick={() => action('Reset', api.robotReset)}>
      {loading === 'Reset' ? '…' : 'Reset'}
    </button>
  </div>

  <div class="manual-mode-row">
    <span class="manual-label">Manual Mode</span>
    <button
      class="manual-toggle"
      class:active={isManualMode}
      disabled={loading === 'ManualMode'}
      onclick={toggleManualMode}
      title="Mode 1 (サーボモード) を維持。Jog のたびのモード切り替えが不要になる。"
    >
      {#if loading === 'ManualMode'}
        …
      {:else if isManualMode}
        ON
      {:else}
        OFF
      {/if}
    </button>
    {#if isManualMode}
      <span class="manual-warn">SERVO MODE — Home/Initial 使用前に OFF にしてください</span>
    {/if}
  </div>
</section>

<style>
  .panel {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
  }
  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  h3 {
    margin: 0;
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .btn-sm {
    padding: 3px 10px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 0.7rem;
    cursor: pointer;
  }
  .btn-sm:hover {
    background: #334155;
  }
  .status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    padding: 8px 12px;
    background: #0f172a;
    border-radius: 6px;
    border: 1px solid #334155;
  }
  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #f87171;
    flex-shrink: 0;
  }
  .status-dot.connected {
    background: #4ade80;
    box-shadow: 0 0 6px #4ade80;
  }
  .status-text {
    font-size: 0.8rem;
    color: #e2e8f0;
    font-weight: 600;
  }
  .mode-badge {
    color: #64748b;
    font-weight: 400;
  }
  .error-badge {
    margin-left: auto;
    font-size: 0.7rem;
    color: #f87171;
    background: #3b1c1c;
    padding: 2px 8px;
    border-radius: 4px;
  }
  .btn-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .btn {
    padding: 10px 20px;
    border: 1px solid #334155;
    border-radius: 6px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn:hover:not(:disabled) {
    background: #334155;
    border-color: #475569;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn.connect {
    background: #0d3320;
    color: #4ade80;
    border-color: #166534;
  }
  .btn.connect:hover:not(:disabled) {
    background: #166534;
  }
  .btn.disconnect {
    background: #3b1c1c;
    color: #f87171;
    border-color: #7f1d1d;
  }
  .btn.disconnect:hover:not(:disabled) {
    background: #7f1d1d;
  }

  .manual-mode-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #1e293b;
    flex-wrap: wrap;
  }
  .manual-label {
    font-size: 0.78rem;
    color: #94a3b8;
    white-space: nowrap;
  }
  .manual-toggle {
    min-width: 52px;
    padding: 5px 14px;
    border-radius: 20px;
    border: 2px solid #334155;
    background: #0f172a;
    color: #64748b;
    font-size: 0.78rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    letter-spacing: 0.05em;
  }
  .manual-toggle.active {
    background: #78350f;
    border-color: #f59e0b;
    color: #fbbf24;
    box-shadow: 0 0 8px rgba(245, 158, 11, 0.4);
  }
  .manual-toggle:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .manual-warn {
    font-size: 0.68rem;
    color: #f59e0b;
    flex-basis: 100%;
  }
</style>
