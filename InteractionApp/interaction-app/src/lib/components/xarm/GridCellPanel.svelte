<script lang="ts">
  import { api } from '$lib/api.svelte';
  import { appState } from '$lib/appState.svelte';
  import type { GridCell } from '$lib/types';

  type CellAction = 'move' | 'pick';

  let cells = $state<GridCell[]>([]);
  let loaded = $state(false);
  let loading = $state(false);
  let actionCell = $state('');
  let cellAction = $state<CellAction>('move');

  // derive grid dimensions
  const maxCol = $derived(cells.reduce((m, c) => Math.max(m, c.col), -1));
  const maxRow = $derived(cells.reduce((m, c) => Math.max(m, c.row), -1));
  const colCount = $derived(maxCol + 1);
  const rowCount = $derived(maxRow + 1);

  function cellAt(col: number, row: number): GridCell | undefined {
    return cells.find((c) => c.col === col && c.row === row);
  }

  async function loadCells() {
    loading = true;
    try {
      const res = await api.robotGridCells();
      cells = res.cells;
      loaded = true;
    } catch (e) {
      appState.addToast(`Failed to load grid cells: ${e}`, 'error');
    } finally {
      loading = false;
    }
  }

  async function onCellClick(col: number, row: number) {
    const key = `${col},${row}`;
    actionCell = key;
    try {
      if (cellAction === 'pick') {
        const res = await api.robotPick(col, row);
        if (res.success) {
          appState.addToast(`Pick (${col},${row}): ${res.message}`, 'success');
        } else {
          appState.addToast(`Pick (${col},${row}): ${res.message}`, 'error');
        }
      } else {
        const res = await api.robotGridMove(col, row);
        if (res.success) {
          appState.addToast(`Move (${col},${row}): ${res.message}`, 'success');
        } else {
          appState.addToast(`Move (${col},${row}): ${res.message}`, 'error');
        }
      }
    } catch (e) {
      appState.addToast(`Cell (${col},${row}) error: ${e}`, 'error');
    } finally {
      actionCell = '';
    }
  }

  async function reload() {
    try {
      await api.robotGridReload();
      await loadCells();
      appState.addToast('Grid map reloaded', 'success');
    } catch (e) {
      appState.addToast(`Reload error: ${e}`, 'error');
    }
  }
</script>

<section class="panel">
  <div class="header">
    <h3>Grid Cells (4×4)</h3>
    <div class="header-actions">
      <div class="mode-toggle">
        <button
          class="mode-btn"
          class:active={cellAction === 'move'}
          onclick={() => (cellAction = 'move')}
        >
          Move
        </button>
        <button
          class="mode-btn pick"
          class:active={cellAction === 'pick'}
          onclick={() => (cellAction = 'pick')}
        >
          Pick
        </button>
      </div>
      <button class="btn-sm" onclick={reload} disabled={loading}>↻</button>
      <button class="btn-sm" onclick={loadCells} disabled={loading}>
        {loading ? '…' : 'Load'}
      </button>
    </div>
  </div>

  {#if !loaded}
    <p class="muted">Click Load to fetch grid cells from server</p>
  {:else if cells.length === 0}
    <p class="muted">No grid cells loaded (grid_pose_map.json empty?)</p>
  {:else}
    <div class="grid" style="grid-template-columns: repeat({colCount}, var(--cell-size, 44px));">
      {#each Array(rowCount) as _, row}
        {#each Array(colCount) as _, col}
          {@const cell = cellAt(col, row)}
          {@const key = `${col},${row}`}
          {@const busy = actionCell === key}
          <button
            class="cell"
            class:exists={!!cell}
            class:busy
            class:pick-mode={cellAction === 'pick'}
            disabled={!cell || busy}
            title={cell
              ? `(${col},${row}) ${cellAction}\nPose: [${cell.pose.map((v) => v.toFixed(0)).join(', ')}]`
              : `(${col},${row}) N/A`}
            onclick={() => onCellClick(col, row)}
          >
            {#if busy}
              …
            {:else}
              {col},{row}
            {/if}
          </button>
        {/each}
      {/each}
    </div>
    <p class="hint">
      Mode: <strong>{cellAction === 'pick' ? '📌 Pick' : '➡️ Move'}</strong>
      · {cells.length} cells loaded
    </p>
  {/if}
</section>

<style>
  .panel {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
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
  }
  .mode-toggle {
    display: flex;
    gap: 2px;
  }
  .mode-btn {
    padding: 3px 10px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #64748b;
    font-size: 0.7rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .mode-btn.active {
    background: #1e3a5f;
    color: #38bdf8;
    border-color: #2563eb;
  }
  .mode-btn.pick.active {
    background: #3b1c1c;
    color: #f87171;
    border-color: #7f1d1d;
  }
  .btn-sm {
    padding: 3px 10px;
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
  .muted {
    color: #475569;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0;
  }
  .hint {
    margin: 8px 0 0;
    font-size: 0.7rem;
    color: #64748b;
  }

  .grid {
    --cell-size: 44px;
    display: grid;
    gap: 4px;
    width: max-content;
    max-width: 100%;
  }
  .cell {
    width: var(--cell-size);
    height: var(--cell-size);
    min-width: 0;
    border: 1px solid #334155;
    border-radius: 6px;
    background: #0f172a;
    color: #475569;
    font-size: 0.62rem;
    font-weight: 600;
    cursor: not-allowed;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    padding: 0;
  }
  .cell.exists {
    background: #1e3a5f;
    color: #38bdf8;
    border-color: #2563eb;
    cursor: pointer;
  }
  .cell.exists:hover:not(:disabled) {
    background: #2563eb;
    color: #fff;
    transform: scale(1.04);
    box-shadow: 0 0 12px rgba(37, 99, 235, 0.4);
  }
  .cell.exists.pick-mode {
    border-color: #dc2626;
    background: #1f1215;
    color: #f87171;
  }
  .cell.exists.pick-mode:hover:not(:disabled) {
    background: #dc2626;
    color: #fff;
    box-shadow: 0 0 12px rgba(220, 38, 38, 0.4);
  }
  .cell.busy {
    opacity: 0.6;
    animation: pulse 0.8s ease-in-out infinite;
  }
  .cell:disabled {
    cursor: not-allowed;
  }
  @media (max-width: 1024px) {
    .grid {
      --cell-size: 40px;
    }
    .cell {
      font-size: 0.6rem;
    }
  }

  @media (max-width: 768px) {
    .grid {
      --cell-size: 38px;
    }
    .cell {
      font-size: 0.58rem;
    }
  }
  @keyframes pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
</style>
