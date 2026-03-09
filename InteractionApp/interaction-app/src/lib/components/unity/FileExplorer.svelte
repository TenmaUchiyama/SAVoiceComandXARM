<script lang="ts">
  import { wsUnity, appState } from '$lib/appState.svelte';
  import { generateRequestId } from '$lib/ws.svelte';
  import JsonViewer from '../JsonViewer.svelte';

  interface FileEntry {
    name: string;
    isDirectory: boolean;
    children?: FileEntry[];
  }

  let tree = $state<FileEntry[]>([]);
  let selectedContent = $state<unknown>(null);
  let selectedPath = $state('');
  let loading = $state(false);

  function requestList(recursive: boolean) {
    loading = true;
    tree = [];
    wsUnity.send('pc_debug_persistent_list_request', {
      request_id: generateRequestId('list'),
      recursive,
    });
  }

  function requestRead(path: string) {
    selectedPath = path;
    selectedContent = null;
    wsUnity.send('pc_debug_read_json_request', {
      request_id: generateRequestId('read'),
      relative_path: path,
    });
  }

  // Listen for responses
  wsUnity.on('pc_debug_persistent_list_response', (data: unknown) => {
    loading = false;
    const d = data as Record<string, unknown>;
    if (d.files) {
      tree = d.files as FileEntry[];
    } else if (Array.isArray(d)) {
      tree = d as FileEntry[];
    }
  });

  wsUnity.on('pc_debug_read_json_response', (data: unknown) => {
    const d = data as Record<string, unknown>;
    if (d.success && d.content) {
      try {
        selectedContent = JSON.parse(String(d.content));
      } catch {
        selectedContent = d.content;
      }
    } else {
      selectedContent = d;
    }
  });
</script>

<section class="panel">
  <div class="header">
    <h3>Unity Files</h3>
    <div class="actions">
      <button class="btn-sm" onclick={() => requestList(false)}>List</button>
      <button class="btn-sm" onclick={() => requestList(true)}>List (recursive)</button>
    </div>
  </div>

  {#if loading}
    <p class="muted">Loading...</p>
  {:else if tree.length === 0}
    <p class="muted">Click List to load files from Unity.</p>
  {:else}
    <div class="tree">
      {#each tree as entry}
        {#if entry.isDirectory}
          <div class="dir">📁 {entry.name}</div>
          {#if entry.children}
            {#each entry.children as child}
              <button class="file-item indent" onclick={() => requestRead(`${entry.name}/${child.name}`)}>
                📄 {child.name}
              </button>
            {/each}
          {/if}
        {:else}
          <button class="file-item" onclick={() => requestRead(entry.name)}>
            📄 {entry.name}
          </button>
        {/if}
      {/each}
    </div>
  {/if}

  {#if selectedContent !== null}
    <div class="preview">
      <h4>Preview: {selectedPath}</h4>
      <JsonViewer data={selectedContent} collapsed={false} />
    </div>
  {/if}
</section>

<style>
  .panel {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .actions {
    display: flex;
    gap: 4px;
  }
  h3 {
    margin: 0;
    font-size: 0.9rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  h4 {
    margin: 0 0 8px;
    font-size: 0.8rem;
    color: #94a3b8;
  }
  .btn-sm {
    padding: 4px 12px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 0.75rem;
    cursor: pointer;
  }
  .btn-sm:hover {
    background: #334155;
  }
  .muted {
    color: #475569;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0;
  }
  .tree {
    max-height: 250px;
    overflow-y: auto;
    margin-bottom: 8px;
  }
  .dir {
    color: #fbbf24;
    font-size: 0.8rem;
    padding: 2px 0;
  }
  .file-item {
    display: block;
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    color: #cbd5e1;
    font-size: 0.8rem;
    padding: 2px 0;
    cursor: pointer;
  }
  .file-item:hover {
    color: #38bdf8;
  }
  .indent {
    padding-left: 20px;
  }
  .preview {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #334155;
  }
</style>
