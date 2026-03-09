<script lang="ts">
  import { wsUnity } from '$lib/appState.svelte';

  const keys = ['w', 'r', 'space', 's', 'a', 'd', 'q', 'e'];

  function sendKey(k: string) {
    wsUnity.sendLegacy('KeyInput', { type: 'key', key: k });
  }
</script>

<section class="panel">
  <h3>Key Input</h3>
  <div class="btn-group">
    {#each keys as k}
      <button class="key-btn" onclick={() => sendKey(k)}>
        {k === 'space' ? '␣' : k.toUpperCase()}
      </button>
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
  .key-btn {
    width: 48px;
    height: 48px;
    border: 1px solid #334155;
    border-radius: 8px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.1s;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .key-btn:hover {
    background: #334155;
    border-color: #475569;
    transform: translateY(-1px);
  }
  .key-btn:active {
    transform: translateY(1px);
    background: #475569;
  }
</style>
