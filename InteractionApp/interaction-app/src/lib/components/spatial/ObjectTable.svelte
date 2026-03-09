<script lang="ts">
  import type { SceneObject } from '$lib/types';

  let { objects }: { objects: SceneObject[] } = $props();
</script>

{#if objects.length > 0}
  <section class="panel">
    <h3>Objects ({objects.length})</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Label</th>
            <th>Color</th>
            <th>Position</th>
          </tr>
        </thead>
        <tbody>
          {#each objects as obj}
            <tr>
              <td class="id">{obj.id}</td>
              <td>{obj.label ?? '-'}</td>
              <td>
                {#if obj.color}
                  <span class="color-chip" style="background:{obj.color}"></span>
                  {obj.color}
                {:else}
                  -
                {/if}
              </td>
              <td class="pos">
                ({obj.position.x.toFixed(2)}, {obj.position.y.toFixed(2)}, {obj.position.z.toFixed(2)})
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>
{/if}

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
  .table-wrap {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }
  th {
    text-align: left;
    padding: 6px 10px;
    color: #64748b;
    border-bottom: 1px solid #334155;
    font-weight: 600;
    white-space: nowrap;
  }
  td {
    padding: 6px 10px;
    color: #cbd5e1;
    border-bottom: 1px solid #1e293b;
  }
  .id {
    font-family: monospace;
    color: #38bdf8;
  }
  .pos {
    font-family: monospace;
    font-size: 0.75rem;
    color: #94a3b8;
  }
  .color-chip {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
    vertical-align: middle;
    margin-right: 4px;
    border: 1px solid #475569;
  }
</style>
