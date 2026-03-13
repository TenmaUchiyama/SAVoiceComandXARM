<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { wsStatus, wsRobot, appState } from '$lib/appState.svelte';
  import StatusBadge from '../StatusBadge.svelte';
  import RobotConnection from './RobotConnection.svelte';
  import GripperControls from './GripperControls.svelte';
  import JogControls from './JogControls.svelte';
  import GridPickPanel from './GridPickPanel.svelte';
  import GridCellPanel from './GridCellPanel.svelte';
  import CalibrationPanel from './CalibrationPanel.svelte';
  import DebugLogPanel from './DebugLogPanel.svelte';

  onMount(() => {
    // XArm タブが表示されたとき Robot WS を接続する
    // (serverBaseUrl に合わせて URL を組み立てる)
    const wsBase = appState.serverBaseUrl.replace(/^http/, 'ws');
    wsRobot.connect(`${wsBase}/robot`);
  });

  onDestroy(() => {
    // タブを離れても切断はしない (autoReconnect で維持)
  });
</script>

<div class="xarm-tab">
  <!-- Row 0: WS indicators -->
  <div class="status-bar">
    <StatusBadge connected={wsStatus.connected} label="Status WS" />
    <StatusBadge connected={wsRobot.connected} label="Robot WS" />
  </div>

  <!-- Row 1: Connection + Gripper -->
  <div class="grid-2col">
    <RobotConnection />
    <GripperControls />
  </div>

  <!-- Row 2: Jog + Grid Cells -->
  <div class="grid-2col">
    <JogControls />
    <GridCellPanel />
  </div>

  <!-- Row 3: Grid Pick (座標) -->
  <GridPickPanel />

  <!-- Row 4: Calibration -->
  <CalibrationPanel />

  <!-- Row 5: Debug Log -->
  <DebugLogPanel />
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
  .grid-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  @media (max-width: 768px) {
    .grid-2col {
      grid-template-columns: 1fr;
    }
  }
</style>
