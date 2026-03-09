<script lang="ts">
  import { appState, wsStatus } from '$lib/appState.svelte';
  import StatusBadge from '../StatusBadge.svelte';
  import BasicControls from './BasicControls.svelte';
  import GripperControls from './GripperControls.svelte';
  import GridPickPanel from './GridPickPanel.svelte';
  import GridMapView from './GridMapView.svelte';
</script>

<div class="xarm-tab">
  <div class="status-bar">
    <StatusBadge connected={wsStatus.connected} label="Status WS" />
    <span class="robot-status" class:enabled={appState.robotEnabled}>
      Robot: {appState.robotEnabled ? '✅ Enabled' : '❌ Disabled'}
    </span>
  </div>

  <div class="grid-2col">
    <BasicControls />
    <GripperControls />
  </div>

  <div class="grid-2col">
    <GridPickPanel />
    <GridMapView />
  </div>

  <div class="jog-notice">
    <p>🔧 Manual Jog controls are planned for v2 (requires server-side <code>/api/robot/jog</code> endpoint)</p>
  </div>
</div>

<style>
  .xarm-tab {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .status-bar {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .robot-status {
    font-size: 0.85rem;
    color: #f87171;
    font-weight: 600;
  }
  .robot-status.enabled {
    color: #4ade80;
  }
  .grid-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .jog-notice {
    background: #1e293b;
    border: 1px dashed #334155;
    border-radius: 8px;
    padding: 16px;
  }
  .jog-notice p {
    margin: 0;
    color: #64748b;
    font-size: 0.8rem;
  }
  .jog-notice code {
    color: #fbbf24;
  }

  @media (max-width: 768px) {
    .grid-2col {
      grid-template-columns: 1fr;
    }
  }
</style>
