<script lang="ts">
  import { api } from '$lib/api.svelte';
  import { appState } from '$lib/appState.svelte';

  let x = $state(0);
  let y = $state(0);
  let loading = $state(false);

  async function pick() {
    loading = true;
    try {
      await api.robotPick(x, y);
      appState.addToast(`Pick at (${x}, ${y}) succeeded`, 'success');
    } catch (e) {
      appState.addToast(`Pick failed: ${e}`, 'error');
    } finally {
      loading = false;
    }
  }
</script>

<section class="panel">
  <h3>Grid Pick</h3>
  <div class="inputs">
    <label>
      <span>X</span>
      <input type="number" bind:value={x} min="0" />
    </label>
    <label>
      <span>Y</span>
      <input type="number" bind:value={y} min="0" />
    </label>
    <button class="btn" disabled={loading} onclick={pick}>
      {loading ? '…' : '📌 Pick'}
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
  .inputs {
    display: flex;
    align-items: flex-end;
    gap: 12px;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  label span {
    font-size: 0.75rem;
    color: #94a3b8;
  }
  input {
    width: 80px;
    padding: 8px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 0.85rem;
  }
  input:focus {
    outline: none;
    border-color: #38bdf8;
  }
  .btn {
    padding: 8px 24px;
    border: 1px solid #334155;
    border-radius: 6px;
    background: #1e3a5f;
    color: #38bdf8;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn:hover:not(:disabled) {
    background: #2563eb;
    color: #fff;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
