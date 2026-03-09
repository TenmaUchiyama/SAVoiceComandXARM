<script lang="ts">
  import { api } from '$lib/api.svelte';
  import { appState } from '$lib/appState.svelte';

  let loading = $state('');

  async function action(name: string, fn: () => Promise<unknown>) {
    loading = name;
    try {
      await fn();
      appState.addToast(`${name} succeeded`, 'success');
    } catch (e) {
      appState.addToast(`${name} failed: ${e}`, 'error');
    } finally {
      loading = '';
    }
  }
</script>

<section class="panel">
  <h3>Basic Controls</h3>
  <div class="btn-group">
    <button class="btn" disabled={loading === 'Home'} onclick={() => action('Home', api.robotHome)}>
      {loading === 'Home' ? '…' : '🏠 Home'}
    </button>
    <button class="btn" disabled={loading === 'Initial'} onclick={() => action('Initial', api.robotInitial)}>
      {loading === 'Initial' ? '…' : '📍 Initial Pos'}
    </button>
    <button class="btn" disabled={loading === 'Reset'} onclick={() => action('Reset', api.robotReset)}>
      {loading === 'Reset' ? '…' : '🔄 Reset'}
    </button>
  </div>
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
</style>
