<script lang="ts">
  import { wsUnity, appState } from '$lib/appState.svelte';
import { api } from '$lib/api.svelte';
  import StatusBadge from '../StatusBadge.svelte';
  import CalibrationPanel from './CalibrationPanel.svelte';
  import KeyPad from './KeyPad.svelte';
  import GridFileList from './GridFileList.svelte';
  import FileExplorer from './FileExplorer.svelte';
  import RawSender from './RawSender.svelte';

  // Import actions — Unity から JSON を取得してサーバーに保存
  async function importGrid() {
    try {
      const res = await api.unityImportGrid();
      appState.addToast(`Grid imported: ${res.filename}`, 'success');
    } catch (e) {
      appState.addToast(`Import Grid failed: ${e}`, 'error');
    }
  }

  async function importRobot() {
    try {
      const res = await api.unityImportRobot();
      appState.addToast(`Robot imported: ${res.filename}`, 'success');
    } catch (e) {
      appState.addToast(`Import Robot failed: ${e}`, 'error');
    }
  }

  async function importPair() {
    await importGrid();
    await importRobot();
  }

  async function restoreAll() {
    try {
      const grids = appState.savedGrids;
      const robots = appState.savedRobots;

      if (grids.length > 0) {
        await api.restoreGrid(grids[0]);
      }
      if (robots.length > 0) {
        await api.restoreRobot(robots[0]);
      }
      appState.addToast('Restore All complete', 'success');
    } catch (e) {
      appState.addToast(`Restore All failed: ${e}`, 'error');
    }
  }

  // Listen for Save events from Unity
  wsUnity.on('SaveGridConfig', (data: unknown) => {
    appState.addToast('Grid config saved from Unity', 'success');
  });

  wsUnity.on('SaveRobotConfig', (data: unknown) => {
    appState.addToast('Robot config saved from Unity', 'success');
  });
</script>

<div class="unity-tab">
  <div class="status-bar">
    <StatusBadge connected={wsUnity.connected} label="Unity WS" />
  </div>

  <div class="grid-2col">
    <CalibrationPanel />
    <KeyPad />
  </div>

  <div class="grid-2col">
    <GridFileList kind="grid" />
    <GridFileList kind="robot" />
  </div>

  <div class="action-bar">
    <button class="btn" onclick={restoreAll}>Restore All</button>
    <button class="btn" onclick={importGrid}>Import Grid</button>
    <button class="btn" onclick={importRobot}>Import Robot</button>
    <button class="btn" onclick={importPair}>Import Pair</button>
  </div>

  <FileExplorer />
  <RawSender />
</div>

<style>
  .unity-tab {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .status-bar {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .grid-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .action-bar {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .btn {
    padding: 8px 20px;
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

  @media (max-width: 768px) {
    .grid-2col {
      grid-template-columns: 1fr;
    }
  }
</style>
