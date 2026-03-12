<script lang="ts">
  import { appState } from '$lib/appState.svelte';
  import { api } from '$lib/api.svelte';
  import type { DebugLogEntry } from '$lib/types';

  let levelFilter = $state<DebugLogEntry['level'] | 'all'>('all');
  let sourceFilter = $state('all');
  let autoScroll = $state(true);

  const filtered = $derived(
    appState.debugLogs.filter((e) => {
      if (levelFilter !== 'all' && e.level !== levelFilter) return false;
      if (sourceFilter !== 'all' && e.source !== sourceFilter) return false;
      return true;
    }),
  );

  const sources = $derived([...new Set(appState.debugLogs.map((e) => e.source))].sort());

  async function fetchHistory() {
    try {
      const res = await api.debugLogs();
      // Merge (push older entries that aren't already present)
      for (const entry of res.logs.reverse()) {
        appState.pushDebugLog(entry);
      }
    } catch (e) {
      appState.addToast(`Failed to fetch debug logs: ${e}`, 'error');
    }
  }

  async function clearLogs() {
    try {
      appState.clearDebugLogs();
      await api.debugLogsClear();
    } catch {
      // ignore
    }
  }

  function levelColor(level: string): string {
    switch (level) {
      case 'error': return '#f87171';
      case 'warn': return '#fbbf24';
      case 'step': return '#818cf8';
      default: return '#4ade80';
    }
  }

  function levelIcon(level: string): string {
    switch (level) {
      case 'error': return '✗';
      case 'warn': return '⚠';
      case 'step': return '→';
      default: return '✓';
    }
  }

  function formatTime(ts: string): string {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('ja-JP', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return ts;
    }
  }
</script>

<section class="panel">
  <div class="header">
    <h3>Server Debug Log</h3>
    <div class="header-actions">
      <select bind:value={levelFilter} class="filter-select">
        <option value="all">All Levels</option>
        <option value="info">Info</option>
        <option value="warn">Warn</option>
        <option value="error">Error</option>
        <option value="step">Step</option>
      </select>
      <select bind:value={sourceFilter} class="filter-select">
        <option value="all">All Sources</option>
        {#each sources as src}
          <option value={src}>{src}</option>
        {/each}
      </select>
      <button class="btn-sm" onclick={fetchHistory}>📥 History</button>
      <button class="btn-sm danger" onclick={clearLogs}>Clear</button>
    </div>
  </div>

  <div class="log-stream">
    {#each filtered as entry, i (entry.ts + i)}
      <div class="log-entry level-{entry.level}">
        <span class="time">{formatTime(entry.ts)}</span>
        <span class="level-icon" style="color: {levelColor(entry.level)}">
          {levelIcon(entry.level)}
        </span>
        <span class="source">{entry.source}</span>
        <span class="message">{entry.message}</span>
        {#if entry.detail}
          <span class="detail">{typeof entry.detail === 'string' ? entry.detail : JSON.stringify(entry.detail)}</span>
        {/if}
      </div>
    {:else}
      <p class="empty">No debug logs. Server actions will appear here in real-time.</p>
    {/each}
  </div>

  <div class="footer">
    <span class="count">{filtered.length} / {appState.debugLogs.length} entries</span>
  </div>
</section>

<style>
  .panel {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }
  h3 {
    margin: 0;
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .filter-select {
    padding: 3px 8px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 0.7rem;
  }
  .filter-select:focus {
    outline: none;
    border-color: #38bdf8;
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
  .btn-sm.danger {
    border-color: #7f1d1d;
    color: #f87171;
  }
  .btn-sm.danger:hover {
    background: #7f1d1d;
  }

  .log-stream {
    flex: 1;
    overflow-y: auto;
    max-height: 360px;
    min-height: 120px;
    border: 1px solid #0f172a;
    border-radius: 4px;
    background: #0a0f1a;
  }
  .log-entry {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 4px 8px;
    border-bottom: 1px solid #111827;
    font-size: 0.75rem;
    line-height: 1.5;
  }
  .log-entry:hover {
    background: #111827;
  }
  .log-entry.level-error {
    background: rgba(248, 113, 113, 0.05);
  }
  .log-entry.level-warn {
    background: rgba(251, 191, 36, 0.05);
  }
  .time {
    color: #475569;
    font-family: monospace;
    font-size: 0.65rem;
    flex-shrink: 0;
    min-width: 60px;
  }
  .level-icon {
    font-weight: 700;
    font-size: 0.8rem;
    flex-shrink: 0;
    width: 16px;
    text-align: center;
  }
  .source {
    color: #94a3b8;
    font-weight: 600;
    font-size: 0.65rem;
    text-transform: uppercase;
    flex-shrink: 0;
    min-width: 48px;
  }
  .message {
    color: #e2e8f0;
  }
  .detail {
    color: #64748b;
    font-family: monospace;
    font-size: 0.65rem;
    word-break: break-all;
  }
  .empty {
    text-align: center;
    color: #475569;
    font-style: italic;
    padding: 32px 0;
    font-size: 0.8rem;
  }
  .footer {
    display: flex;
    justify-content: flex-end;
  }
  .count {
    font-size: 0.65rem;
    color: #475569;
  }
</style>
