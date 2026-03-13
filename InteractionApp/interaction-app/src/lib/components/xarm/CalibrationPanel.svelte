<script lang="ts">
  import { onMount } from 'svelte';
  import { appState } from '$lib/appState.svelte';
  import { api } from '$lib/api.svelte';

  // --- state ---
  let mode = $state<'grid' | 'place'>('grid');

  // Grid mode
  const COLS = 4;
  const ROWS = 4;
  let selectedCol = $state(0);
  let selectedRow = $state(0);
  let recordedGridKeys = $state<Set<string>>(new Set());

  // Place mode
  let placeKey = $state('default');
  let recordedPlaceKeys = $state<string[]>([]);

  let busy = $state(false);
  let lastMsg = $state('');

  // --- load calibration status ---
  async function loadStatus() {
    try {
      const s = await api.robotCalibStatus();
      recordedGridKeys = new Set(s.grid_keys);
      recordedPlaceKeys = s.place_keys;
    } catch {
      // ignore
    }
  }

  onMount(() => {
    loadStatus();
  });

  // --- helpers ---
  function cellKey(col: number, row: number) {
    return `${col},${row}`;
  }

  function isRecorded(col: number, row: number) {
    return recordedGridKeys.has(cellKey(col, row));
  }

  function selectCell(col: number, row: number) {
    selectedCol = col;
    selectedRow = row;
  }

  // --- record actions ---
  async function recordGrid() {
    busy = true;
    lastMsg = '';
    try {
      const res = await api.robotCalibRecordGrid(selectedCol, selectedRow);
      lastMsg = res.message ?? '';
      if (res.success) {
        appState.addToast(`記録完了: (${selectedCol},${selectedRow})`, 'success');
        await loadStatus();
        // 次のセルへ自動進める
        advanceCell();
      } else {
        appState.addToast(`記録失敗: ${res.message}`, 'error');
      }
    } catch (e: any) {
      appState.addToast(`エラー: ${e.message}`, 'error');
    } finally {
      busy = false;
    }
  }

  async function recordPlace() {
    if (!placeKey.trim()) return;
    busy = true;
    lastMsg = '';
    try {
      const res = await api.robotCalibRecordPlace(placeKey.trim());
      lastMsg = res.message ?? '';
      if (res.success) {
        appState.addToast(`Place記録完了: "${placeKey}"`, 'success');
        await loadStatus();
      } else {
        appState.addToast(`記録失敗: ${res.message}`, 'error');
      }
    } catch (e: any) {
      appState.addToast(`エラー: ${e.message}`, 'error');
    } finally {
      busy = false;
    }
  }

  // 記録後に次のセルへ自動移動 (行優先: 0,0→1,0→...→3,0→0,1→...)
  function advanceCell() {
    let nextCol = selectedCol + 1;
    let nextRow = selectedRow;
    if (nextCol >= COLS) {
      nextCol = 0;
      nextRow = selectedRow + 1;
    }
    if (nextRow < ROWS) {
      selectedCol = nextCol;
      selectedRow = nextRow;
    }
  }

  let recordedCount = $derived(recordedGridKeys.size);
  let totalCells = $derived(COLS * ROWS);
  let pos = $derived(appState.robotStatus?.position);
</script>

<section class="panel">
  <div class="panel-header">
    <h3>Calibration</h3>
    <div class="mode-tabs">
      <button class="mode-btn" class:active={mode === 'grid'} onclick={() => (mode = 'grid')}>
        Grid
      </button>
      <button class="mode-btn" class:active={mode === 'place'} onclick={() => (mode = 'place')}>
        Place
      </button>
    </div>
  </div>

  <!-- Current Position -->
  <div class="pos-bar">
    <span class="pos-label">現在位置</span>
    {#if pos}
      <span class="pos-val">
        X:{pos[0]?.toFixed(1)}
        Y:{pos[1]?.toFixed(1)}
        Z:{pos[2]?.toFixed(1)}
      </span>
    {:else}
      <span class="pos-none">—</span>
    {/if}
  </div>

  <!-- Grid Mode -->
  {#if mode === 'grid'}
    <div class="progress-bar-wrap">
      <div class="progress-bar" style="width: {(recordedCount / totalCells) * 100}%"></div>
    </div>
    <p class="progress-label">{recordedCount} / {totalCells} 記録済み</p>

    <div class="grid-map">
      {#each Array(ROWS) as _, row}
        {#each Array(COLS) as _, col}
          {@const key = cellKey(col, row)}
          {@const recorded = recordedGridKeys.has(key)}
          {@const selected = selectedCol === col && selectedRow === row}
          <button
            class="cell"
            class:recorded
            class:selected
            onclick={() => selectCell(col, row)}
          >
            <span class="cell-label">{col},{row}</span>
            {#if recorded}
              <span class="cell-check">✓</span>
            {/if}
          </button>
        {/each}
      {/each}
    </div>

    <div class="target-row">
      <span class="target-label">ターゲット:</span>
      <span class="target-val">({selectedCol}, {selectedRow})</span>
    </div>

    <button
      class="record-btn"
      disabled={busy || !appState.robotStatus?.connected}
      onclick={recordGrid}
    >
      {busy ? '記録中…' : `⏺ Record (${selectedCol},${selectedRow})`}
    </button>

  <!-- Place Mode -->
  {:else}
    <div class="place-keys">
      {#if recordedPlaceKeys.length > 0}
        <span class="pos-label">記録済み:</span>
        {#each recordedPlaceKeys as k}
          <button
            class="key-chip"
            class:active={placeKey === k}
            onclick={() => (placeKey = k)}
          >{k}</button>
        {/each}
      {:else}
        <span class="pos-none">まだ記録なし</span>
      {/if}
    </div>

    <div class="place-input-row">
      <label class="pos-label" for="place-key-input">Place key</label>
      <input
        id="place-key-input"
        class="place-input"
        type="text"
        bind:value={placeKey}
        placeholder="default"
      />
    </div>

    <button
      class="record-btn place"
      disabled={busy || !appState.robotStatus?.connected || !placeKey.trim()}
      onclick={recordPlace}
    >
      {busy ? '記録中…' : `⏺ Record "${placeKey}"`}
    </button>
  {/if}

  {#if lastMsg}
    <p class="last-msg">{lastMsg}</p>
  {/if}
</section>

<style>
  .panel {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  h3 {
    margin: 0;
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .mode-tabs {
    display: flex;
    gap: 4px;
  }
  .mode-btn {
    padding: 4px 12px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #94a3b8;
    font-size: 0.75rem;
    cursor: pointer;
  }
  .mode-btn.active {
    background: #1e3a5f;
    color: #38bdf8;
    border-color: #2563eb;
  }

  .pos-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.75rem;
  }
  .pos-label { color: #64748b; }
  .pos-val { color: #38bdf8; }
  .pos-none { color: #475569; }

  .progress-bar-wrap {
    height: 4px;
    background: #0f172a;
    border-radius: 2px;
    overflow: hidden;
  }
  .progress-bar {
    height: 100%;
    background: #22c55e;
    transition: width 0.3s;
  }
  .progress-label {
    margin: 0;
    font-size: 0.72rem;
    color: #64748b;
    text-align: right;
  }

  .grid-map {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
  }
  .cell {
    padding: 8px 4px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #64748b;
    font-size: 0.7rem;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    transition: all 0.1s;
  }
  .cell:hover { background: #1e293b; border-color: #475569; }
  .cell.recorded {
    background: #14532d;
    border-color: #22c55e;
    color: #86efac;
  }
  .cell.selected {
    border-color: #3b82f6;
    outline: 2px solid #3b82f6;
    color: #93c5fd;
  }
  .cell.selected.recorded { border-color: #3b82f6; }
  .cell-label { font-family: monospace; }
  .cell-check { font-size: 0.65rem; color: #22c55e; }

  .target-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
  }
  .target-label { color: #64748b; }
  .target-val { color: #e2e8f0; font-family: monospace; font-weight: 600; }

  .record-btn {
    padding: 10px;
    border: none;
    border-radius: 6px;
    background: #dc2626;
    color: #fff;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  .record-btn:hover:not(:disabled) { background: #b91c1c; }
  .record-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .record-btn.place { background: #7c3aed; }
  .record-btn.place:hover:not(:disabled) { background: #6d28d9; }

  .place-keys {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
  }
  .key-chip {
    padding: 3px 10px;
    border: 1px solid #334155;
    border-radius: 12px;
    background: #0f172a;
    color: #94a3b8;
    font-size: 0.72rem;
    cursor: pointer;
  }
  .key-chip.active {
    background: #4c1d95;
    border-color: #7c3aed;
    color: #c4b5fd;
  }

  .place-input-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .place-input {
    flex: 1;
    padding: 6px 10px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 0.8rem;
  }
  .place-input:focus {
    outline: none;
    border-color: #7c3aed;
  }

  .last-msg {
    margin: 0;
    font-size: 0.7rem;
    color: #64748b;
    font-family: monospace;
  }
</style>
