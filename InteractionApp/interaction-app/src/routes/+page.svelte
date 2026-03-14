<script lang="ts">
  import { appState, wsUnity, wsSpatial, wsStatus, wsRobot } from '$lib/appState.svelte';
  import { apiConfig } from '$lib/api.svelte';
  import TabContainer from '$lib/components/TabContainer.svelte';
  import StatusBadge from '$lib/components/StatusBadge.svelte';
  import UnityTab from '$lib/components/unity/UnityTab.svelte';
  import XArmTab from '$lib/components/xarm/XArmTab.svelte';
  import SpatialTab from '$lib/components/spatial/SpatialTab.svelte';
  import GridEditor from '$lib/components/unity/GridEditor.svelte';
  import LogPanel from '$lib/components/LogPanel.svelte';

  // Connection settings
  const FIXED_PORT = 8765;

  function extractIp(url: string): string {
    try { return new URL(url).hostname; } catch { return 'localhost'; }
  }

  let serverIp = $state(extractIp(appState.serverBaseUrl));
  let showSettings = $state(false);

  function connectAll() {
    const unityUrl = `ws://${serverIp}:${FIXED_PORT}`;
    const serverUrl = `http://${serverIp}:${FIXED_PORT}`;

    appState.unityWsUrl = unityUrl;
    appState.serverBaseUrl = serverUrl;
    apiConfig.serverBaseUrl = serverUrl;

    wsUnity.connect(unityUrl);
    wsSpatial.connect(`ws://${serverIp}:${FIXED_PORT}/spatial`);
    wsStatus.connect(`ws://${serverIp}:${FIXED_PORT}/status`);
    wsRobot.connect(`ws://${serverIp}:${FIXED_PORT}/robot`);

    showSettings = false;
  }

  function disconnectAll() {
    wsUnity.close();
    wsSpatial.close();
    wsStatus.close();
    wsRobot.close();
  }
</script>

<div class="app">
  <!-- Header -->
  <header>
    <div class="header-left">
      <h1>InteractionApp</h1>
      <TabContainer />
    </div>
    <div class="header-right">
      <StatusBadge connected={wsUnity.connected} label="Unity" />
      <StatusBadge connected={wsSpatial.connected} label="Spatial" />
      <StatusBadge connected={wsStatus.connected} label="Status" />
      <StatusBadge connected={wsRobot.connected} label="Robot" />
      <button
        class="lang-btn"
        onclick={() => {
          const next = appState.language === 'en' ? 'ja' : 'en';
          appState.language = next;
          wsUnity.send('set_language', { language: next });
        }}
      >
        {appState.language === 'ja' ? 'JA' : 'EN'}
      </button>
      <button class="gear-btn" onclick={() => (showSettings = !showSettings)}>⚙️</button>
    </div>
  </header>

  <!-- Connection Settings Bar -->
  {#if showSettings}
    <div class="settings-bar">
      <label>
        <span>IP Address</span>
        <input type="text" bind:value={serverIp} placeholder="192.168.1.100" />
      </label>
      <span class="fixed-label">ws:// :{FIXED_PORT}</span>
      <button class="btn connect" onclick={connectAll}>Connect All</button>
      <button class="btn disconnect" onclick={disconnectAll}>Disconnect</button>
    </div>
  {/if}

  <!-- Toast notifications -->
  {#if appState.toasts.length > 0}
    <div class="toast-container">
      {#each appState.toasts as toast (toast.id)}
        <div class="toast toast-{toast.type}">
          {toast.message}
        </div>
      {/each}
    </div>
  {/if}

  <!-- Main content -->
  <main>
    {#if appState.activeTab === 'unity'}
      <UnityTab />
    {:else if appState.activeTab === 'xarm'}
      <XArmTab />
    {:else if appState.activeTab === 'spatial'}
      <SpatialTab />
    {:else if appState.activeTab === 'grid'}
      <GridEditor />
    {:else if appState.activeTab === 'log'}
      <LogPanel />
    {/if}
  </main>
</div>

<style>
  :global(*) {
    box-sizing: border-box;
  }
  :global(body) {
    margin: 0;
    padding: 0;
    background: #0a0f1a;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  :global(::-webkit-scrollbar) {
    width: 8px;
    height: 8px;
  }
  :global(::-webkit-scrollbar-track) {
    background: #0f172a;
  }
  :global(::-webkit-scrollbar-thumb) {
    background: #334155;
    border-radius: 4px;
  }
  :global(::-webkit-scrollbar-thumb:hover) {
    background: #475569;
  }

  .app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #0f172a;
    border-bottom: 2px solid #1e293b;
    padding: 0 16px;
  }
  .header-left {
    display: flex;
    align-items: center;
    gap: 24px;
  }
  h1 {
    font-size: 1rem;
    font-weight: 700;
    color: #38bdf8;
    margin: 0;
    white-space: nowrap;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .lang-btn {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 0.8rem;
    font-weight: 700;
    color: #38bdf8;
    transition: all 0.15s;
    min-width: 40px;
    text-align: center;
  }
  .lang-btn:hover {
    background: #334155;
    border-color: #38bdf8;
  }
  .gear-btn {
    background: none;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.15s;
  }
  .gear-btn:hover {
    background: #1e293b;
  }

  .settings-bar {
    display: flex;
    align-items: flex-end;
    gap: 12px;
    padding: 12px 16px;
    background: #0f172a;
    border-bottom: 1px solid #1e293b;
  }
  .settings-bar label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 0 0 auto;
    width: 220px;
  }
  .fixed-label {
    font-size: 0.75rem;
    color: #475569;
    font-family: monospace;
    align-self: flex-end;
    padding-bottom: 9px;
  }
  .settings-bar label span {
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
  }
  .settings-bar input {
    padding: 8px 12px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 0.8rem;
    font-family: monospace;
  }
  .settings-bar input:focus {
    outline: none;
    border-color: #38bdf8;
  }
  .btn {
    padding: 8px 20px;
    border: none;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;
  }
  .btn.connect {
    background: #2563eb;
    color: #fff;
  }
  .btn.connect:hover {
    background: #3b82f6;
  }
  .btn.disconnect {
    background: #1e293b;
    color: #f87171;
    border: 1px solid #7f1d1d;
  }
  .btn.disconnect:hover {
    background: #7f1d1d;
  }

  .toast-container {
    position: fixed;
    top: 60px;
    right: 16px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 380px;
  }
  .toast {
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    animation: slideIn 0.2s ease-out;
  }
  .toast-info {
    background: #1e3a5f;
    color: #38bdf8;
    border: 1px solid #2563eb;
  }
  .toast-success {
    background: #0d3320;
    color: #4ade80;
    border: 1px solid #166534;
  }
  .toast-error {
    background: #3b1c1c;
    color: #f87171;
    border: 1px solid #7f1d1d;
  }
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  main {
    flex: 1;
    padding: 16px;
    overflow-y: auto;
  }

  /* --- Tablet portrait (768px–1024px) --- */
  @media (max-width: 1024px) {
    header {
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px 12px;
    }
    .header-left {
      gap: 12px;
      flex: 1 1 100%;
    }
    .header-right {
      flex-wrap: wrap;
      gap: 6px;
      flex: 1 1 100%;
      justify-content: flex-end;
    }
    .settings-bar {
      flex-wrap: wrap;
      gap: 8px;
      padding: 10px 12px;
    }
    .settings-bar label {
      width: 180px;
    }
    .toast-container {
      max-width: 300px;
      right: 12px;
    }
    main {
      padding: 12px;
    }
  }

  /* --- Mobile (≤768px) --- */
  @media (max-width: 768px) {
    .header-left {
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
    }
    .header-right {
      justify-content: flex-start;
    }
    .settings-bar label {
      width: 100%;
    }
    main {
      padding: 8px;
    }
  }
</style>
