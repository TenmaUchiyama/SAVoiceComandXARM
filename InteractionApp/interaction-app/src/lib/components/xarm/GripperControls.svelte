<script lang="ts">
  import { api } from '$lib/api.svelte';
  import { appState } from '$lib/appState.svelte';

  let loading = $state('');

  async function gripperAction(action_name: 'open' | 'close') {
    loading = action_name;
    try {
      await api.robotGripper(action_name);
      appState.addToast(`Gripper ${action_name}`, 'success');
    } catch (e) {
      appState.addToast(`Gripper ${action_name} failed: ${e}`, 'error');
    } finally {
      loading = '';
    }
  }
</script>

<section class="panel">
  <h3>Gripper</h3>
  <div class="btn-group">
    <button class="btn open" disabled={loading !== ''} onclick={() => gripperAction('open')}>
      {loading === 'open' ? '…' : '✋ Open'}
    </button>
    <button class="btn close" disabled={loading !== ''} onclick={() => gripperAction('close')}>
      {loading === 'close' ? '…' : '✊ Close'}
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
    gap: 8px;
  }
  .btn {
    flex: 1;
    padding: 12px 20px;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn.open {
    background: #0d3320;
    color: #4ade80;
    border-color: #166534;
  }
  .btn.open:hover:not(:disabled) {
    background: #166534;
  }
  .btn.close {
    background: #3b1c1c;
    color: #f87171;
    border-color: #7f1d1d;
  }
  .btn.close:hover:not(:disabled) {
    background: #7f1d1d;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
