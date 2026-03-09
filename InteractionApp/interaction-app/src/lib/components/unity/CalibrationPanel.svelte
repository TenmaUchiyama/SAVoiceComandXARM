<script lang="ts">
  import { wsUnity } from '$lib/appState.svelte';
  import { generateRequestId } from '$lib/ws.svelte';

  const actions = [
    { label: 'Teach', action: 'teach' },
    { label: 'Restore', action: 'restore' },
    { label: 'Record', action: 'record' },
    { label: 'Robot', action: 'robot' },
    { label: 'Clear', action: 'clear' },
    { label: 'Status', action: 'status' },
  ] as const;

  function sendCalibration(action: string) {
    wsUnity.send('pc_debug_calibration_request', {
      request_id: generateRequestId('calib'),
      action,
    });
  }
</script>

<section class="panel">
  <h3>Calibration</h3>
  <div class="btn-group">
    {#each actions as { label, action }}
      <button class="btn" onclick={() => sendCalibration(action)}>{label}</button>
    {/each}
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
</style>
