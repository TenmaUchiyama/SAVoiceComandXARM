<script lang="ts">
  let { data, collapsed = true }: { data: unknown; collapsed?: boolean } = $props();
  let isCollapsed = $state(collapsed);

  function format(d: unknown): string {
    try {
      return JSON.stringify(d, null, 2);
    } catch {
      return String(d);
    }
  }

  const preview = $derived(
    typeof data === 'string'
      ? data.length > 80
        ? data.slice(0, 80) + '…'
        : data
      : JSON.stringify(data)?.slice(0, 80) + (JSON.stringify(data)?.length ?? 0 > 80 ? '…' : '')
  );
</script>

<div class="json-viewer">
  <button class="toggle" onclick={() => (isCollapsed = !isCollapsed)}>
    <span class="arrow" class:open={!isCollapsed}>▶</span>
    {#if isCollapsed}
      <code class="preview">{preview}</code>
    {/if}
  </button>
  {#if !isCollapsed}
    <pre class="expanded"><code>{format(data)}</code></pre>
  {/if}
</div>

<style>
  .json-viewer {
    font-size: 0.8rem;
  }
  .toggle {
    background: none;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    padding: 2px 4px;
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    text-align: left;
  }
  .toggle:hover {
    color: #e2e8f0;
  }
  .arrow {
    display: inline-block;
    transition: transform 0.15s;
    font-size: 0.65rem;
  }
  .arrow.open {
    transform: rotate(90deg);
  }
  .preview {
    color: #64748b;
    font-size: 0.75rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 500px;
  }
  .expanded {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 4px 0 4px 16px;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
  }
  .expanded code {
    color: #a5f3fc;
    font-size: 0.75rem;
    white-space: pre;
  }
</style>
