<script lang="ts">
  import { appState } from '$lib/appState.svelte';
  import { api } from '$lib/api.svelte';

  let {
    kind,
  }: {
    kind: 'grid' | 'robot';
  } = $props();

  let files = $derived(kind === 'grid' ? appState.savedGrids : appState.savedRobots);
  let loading = $state(false);

  async function loadFiles() {
    loading = true;
    try {
      if (kind === 'grid') {
        appState.savedGrids = await api.listGrids();
      } else {
        appState.savedRobots = await api.listRobots();
      }
    } catch (e) {
      appState.addToast(`Failed to load ${kind} files: ${e}`, 'error');
    } finally {
      loading = false;
    }
  }

  async function restore(filename: string) {
    try {
      if (kind === 'grid') {
        await api.restoreGrid(filename);
      } else {
        await api.restoreRobot(filename);
      }
      appState.addToast(`Restored ${kind}: ${filename}`, 'success');
    } catch (e) {
      appState.addToast(`Restore failed: ${e}`, 'error');
    }
  }
</script>

<section class="panel">
  <div class="header">
    <h3>{kind === 'grid' ? 'Grid Configs' : 'Robot Markers'}</h3>
    <button class="btn-sm" onclick={loadFiles} disabled={loading}>
      {loading ? '…' : 'Refresh'}
    </button>
  </div>

  {#if files.length === 0}
    <p class="empty">No files loaded. Click Refresh.</p>
  {:else}
    <ul class="file-list">
      {#each files as file}
        <li>
          <span class="filename">{file}</span>
          <button class="btn-sm" onclick={() => restore(file)}>Restore</button>
        </li>
      {/each}
    </ul>
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
  .empty {
    color: #475569;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0;
  }
  .file-list {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 200px;
    overflow-y: auto;
  }
  .file-list li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 8px;
    border-bottom: 1px solid #1e293b;
  }
  .file-list li:last-child {
    border-bottom: none;
  }
  .filename {
    color: #cbd5e1;
    font-size: 0.8rem;
    font-family: monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 250px;
  }
</style>
