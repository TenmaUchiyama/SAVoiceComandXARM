<script lang="ts">
  import type { TabId } from '$lib/types';
  import { appState } from '$lib/appState.svelte';

  const tabs: { id: TabId; label: string }[] = [
    { id: 'unity', label: 'Unity' },
    { id: 'xarm', label: 'XArm' },
    { id: 'spatial', label: 'Spatial' },
    { id: 'grid', label: 'Grid' },
    { id: 'log', label: 'Log' },
  ];
</script>

<nav class="tab-bar">
  {#each tabs as tab}
    <button
      class="tab-btn"
      class:active={appState.activeTab === tab.id}
      onclick={() => (appState.activeTab = tab.id)}
    >
      {tab.label}
    </button>
  {/each}
</nav>

<style>
  .tab-bar {
    display: flex;
    gap: 2px;
    background: #0f172a;
    padding: 4px 8px 0;
    border-bottom: 2px solid #1e293b;
  }
  .tab-btn {
    padding: 8px 20px;
    border: none;
    border-radius: 8px 8px 0 0;
    background: #1e293b;
    color: #94a3b8;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .tab-btn:hover {
    background: #334155;
    color: #e2e8f0;
  }
  .tab-btn.active {
    background: #1e3a5f;
    color: #38bdf8;
    box-shadow: inset 0 -2px 0 #38bdf8;
  }

  @media (max-width: 1024px) {
    .tab-bar {
      gap: 1px;
      padding: 4px 4px 0;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }
    .tab-btn {
      padding: 6px 14px;
      font-size: 0.8rem;
      flex-shrink: 0;
    }
  }

  @media (max-width: 768px) {
    .tab-btn {
      padding: 6px 10px;
      font-size: 0.75rem;
    }
  }
</style>
