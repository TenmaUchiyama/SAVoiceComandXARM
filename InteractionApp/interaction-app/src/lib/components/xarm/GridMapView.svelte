<script lang="ts">
  import { api } from '$lib/api.svelte';
  import { appState } from '$lib/appState.svelte';

  interface GridCell {
    x: number;
    y: number;
    pose?: unknown;
  }

  let gridMap = $state<Record<string, unknown>>({});
  let rows = $state(0);
  let cols = $state(0);
  let loaded = $state(false);
  let loading = $state(false);

  async function loadGrid() {
    loading = true;
    try {
      // Try to get grid_pose_map from server
      const data = await api.getGrid('grid_pose_map.json');
      gridMap = data as Record<string, unknown>;
      // Detect dimensions
      const keys = Object.keys(gridMap).filter((k) => k.match(/^\d+_\d+$/));
      let maxR = 0, maxC = 0;
      for (const k of keys) {
        const [r, c] = k.split('_').map(Number);
        if (r > maxR) maxR = r;
        if (c > maxC) maxC = c;
      }
      rows = maxR + 1;
      cols = maxC + 1;
      loaded = true;
    } catch (e) {
      appState.addToast(`Failed to load grid map: ${e}`, 'error');
    } finally {
      loading = false;
    }
  }

  async function pickCell(r: number, c: number) {
    try {
      await api.robotPick(c, r);
      appState.addToast(`Pick at (${c}, ${r}) sent`, 'success');
    } catch (e) {
      appState.addToast(`Pick failed: ${e}`, 'error');
    }
  }
</script>

<section class="panel">
  <div class="header">
    <h3>Grid Map</h3>
    <button class="btn-sm" onclick={loadGrid} disabled={loading}>
      {loading ? '…' : 'Load'}
    </button>
  </div>

  {#if !loaded}
    <p class="muted">Click Load to fetch grid_pose_map.json</p>
  {:else if rows === 0}
    <p class="muted">Grid map is empty</p>
  {:else}
    <div class="grid" style="grid-template-columns: repeat({cols}, 1fr);">
      {#each Array(rows) as _, r}
        {#each Array(cols) as _, c}
          {@const key = `${r}_${c}`}
          {@const exists = key in gridMap}
          <button
            class="cell"
            class:exists
            disabled={!exists}
            title="({c}, {r})"
            onclick={() => pickCell(r, c)}
          >
            {c},{r}
          </button>
        {/each}
      {/each}
    </div>
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
  }
  h3 {
    margin: 0;
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
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
  .muted {
    color: #475569;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0;
  }
  .grid {
    display: grid;
    gap: 4px;
  }
  .cell {
    aspect-ratio: 1;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #475569;
    font-size: 0.65rem;
    cursor: not-allowed;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.1s;
  }
  .cell.exists {
    background: #1e3a5f;
    color: #38bdf8;
    border-color: #2563eb;
    cursor: pointer;
  }
  .cell.exists:hover {
    background: #2563eb;
    color: #fff;
    transform: scale(1.05);
  }
</style>
