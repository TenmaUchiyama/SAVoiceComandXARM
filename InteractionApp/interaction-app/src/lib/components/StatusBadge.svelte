<script lang="ts">
  let { connected, label = '' }: { connected: boolean; label?: string } = $props();
</script>

<span class="badge" class:connected class:disconnected={!connected}>
  <span class="dot"></span>
  {#if label}{label}: {/if}{connected ? 'Connected' : 'Disconnected'}
</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .connected {
    background: #0d3320;
    color: #4ade80;
  }
  .disconnected {
    background: #3b1c1c;
    color: #f87171;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .connected .dot {
    background: #4ade80;
    box-shadow: 0 0 6px #4ade80;
  }
  .disconnected .dot {
    background: #f87171;
  }
</style>
