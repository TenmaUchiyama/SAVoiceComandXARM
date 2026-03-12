<script lang="ts">
  import { appState } from '$lib/appState.svelte';
  import { api } from '$lib/api.svelte';

  const actions = [
    { label: 'Teach', action: 'teach' },
    { label: 'Restore', action: 'restore' },
    { label: 'Record', action: 'record' },
    { label: 'Robot', action: 'robot' },
    { label: 'Clear', action: 'clear' },
    { label: 'Status', action: 'status' },
  ] as const;

  async function sendCalibration(action: string) {
    try {
      await api.unityCalib(action);
    } catch (e) {
      appState.addToast(`Calibration failed (${action}): ${e}`, 'error');
    }
  }
</script>

<section class="panel">
  <h3>Calibration</h3>
  <div class="btn-group">
    {#each actions as { label, action }}
      <button class="btn" onclick={() => sendCalibration(action)}>{label}</button>
    {/each}
  </div>
  <h3 class="sub-heading">Grid Visual</h3>
  <div class="btn-group">
    <button class="btn btn-show" onclick={() => sendCalibration('grid_show')}>Show Grid</button>
    <button class="btn btn-hide" onclick={() => sendCalibration('grid_hide')}>Hide Grid</button>
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
    padding: 8px 16px;
    border: 1px solid #334155;
    border-radius: 6px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn:hover {
    background: #334155;
    border-color: #475569;
  }
  .sub-heading {
    margin: 12px 0 8px;
  }
  .btn-show:hover {
    background: #14532d;
    border-color: #16a34a;
  }
  .btn-hide:hover {
    background: #450a0a;
    border-color: #dc2626;
  }
</style>
