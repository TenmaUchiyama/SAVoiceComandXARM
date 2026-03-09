<script lang="ts">
  import type { LogDirection, LogSource } from '$lib/types';
  import { logStore } from '$lib/logStore.svelte';
  import JsonViewer from './JsonViewer.svelte';

  let directionFilter = $state<LogDirection | 'ALL'>('ALL');
  let sourceFilter = $state<LogSource | 'ALL'>('ALL');
  let eventFilter = $state('');

  const filtered = $derived(logStore.filtered(directionFilter, sourceFilter, eventFilter));

  function exportLogs() {
    const content = logStore.exportJsonLines();
    const blob = new Blob([content], { type: 'application/jsonl' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString().replace(/[:.]/g, '-')}.jsonl`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function formatTime(d: Date): string {
    return d.toLocaleTimeString('ja-JP', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    } as Intl.DateTimeFormatOptions);
  }
</script>

<div class="log-tab">
  <div class="toolbar">
    <div class="filters">
      <select bind:value={directionFilter}>
        <option value="ALL">All Directions</option>
        <option value="TX">TX (→)</option>
        <option value="RX">RX (←)</option>
      </select>

      <select bind:value={sourceFilter}>
        <option value="ALL">All Sources</option>
        <option value="unity">Unity</option>
        <option value="spatial">Spatial</option>
        <option value="status">Status</option>
        <option value="http">HTTP</option>
      </select>

      <input
        type="text"
        bind:value={eventFilter}
        placeholder="Filter by event name..."
      />
    </div>

    <div class="actions">
      <span class="count">{filtered.length} entries</span>
      <button class="btn-sm" onclick={exportLogs}>Export</button>
      <button class="btn-sm danger" onclick={() => logStore.clear()}>Clear</button>
    </div>
  </div>

  <div class="log-stream">
    {#each filtered as entry (entry.id)}
      <div class="log-entry dir-{entry.direction.toLowerCase()} src-{entry.source}">
        <span class="time">{formatTime(entry.timestamp)}</span>
        <span class="dir">{entry.direction === 'TX' ? '→' : '←'}</span>
        <span class="source">{entry.source}</span>
        <span class="event">{entry.event}</span>
        <div class="data">
          <JsonViewer data={entry.data} />
        </div>
      </div>
    {:else}
      <p class="empty">No log entries{eventFilter ? ' matching filter' : ''}.</p>
    {/each}
  </div>
</div>

<style>
  .log-tab {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
  }
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  .filters {
    display: flex;
    gap: 6px;
  }
  select, .filters input {
    padding: 6px 10px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 0.8rem;
  }
  select:focus, .filters input:focus {
    outline: none;
    border-color: #38bdf8;
  }
  .filters input {
    width: 200px;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .count {
    font-size: 0.75rem;
    color: #64748b;
  }
  .btn-sm {
    padding: 4px 12px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 0.75rem;
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
    min-height: 0;
    max-height: calc(100vh - 240px);
  }
  .log-entry {
    display: grid;
    grid-template-columns: 90px 20px 60px 1fr;
    gap: 8px;
    align-items: start;
    padding: 6px 8px;
    border-bottom: 1px solid #1e293b;
    font-size: 0.8rem;
  }
  .log-entry:hover {
    background: #1e293b;
  }
  .time {
    color: #475569;
    font-family: monospace;
    font-size: 0.7rem;
  }
  .dir {
    font-weight: 700;
  }
  .dir-tx .dir { color: #fbbf24; }
  .dir-rx .dir { color: #38bdf8; }
  .source {
    font-size: 0.7rem;
    text-transform: uppercase;
    font-weight: 600;
  }
  .src-unity .source { color: #a78bfa; }
  .src-spatial .source { color: #34d399; }
  .src-status .source { color: #fbbf24; }
  .src-http .source { color: #f97316; }
  .event {
    color: #e2e8f0;
    font-family: monospace;
    font-weight: 600;
  }
  .data {
    grid-column: 1 / -1;
    margin-left: 118px;
  }
  .empty {
    text-align: center;
    color: #475569;
    font-style: italic;
    padding: 40px 0;
  }
</style>
