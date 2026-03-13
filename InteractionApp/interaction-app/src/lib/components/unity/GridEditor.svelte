<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api.svelte";
  import { appState } from "$lib/appState.svelte";

  let gridData = $state<any[]>([]);
  let filename = $state("");
  let loading = $state(true);
  let selectedColor = $state("red");

  const colors = [
    { id: "unknown", label: "Unknown", hex: "#475569" },
    { id: "black", label: "Black", hex: "#000000" },
    { id: "white", label: "White", hex: "#ffffff" },
    { id: "red", label: "Red", hex: "#ef4444" },
    { id: "blue", label: "Blue", hex: "#3b82f6" },
    { id: "green", label: "Green", hex: "#22c55e" },
    { id: "yellow", label: "Yellow", hex: "#eab308" },
    { id: "purple", label: "Purple", hex: "#a855f7" },
    { id: "orange", label: "Orange", hex: "#f97316" },
  ];

  async function loadGrid() {
    loading = true;
    try {
      const res = await api.getLatestGrid();
      gridData = res.data;
      filename = res.filename;
    } catch (e) {
      appState.addToast(`Failed to load grid: ${e}`, "error");
    } finally {
      loading = false;
    }
  }

  async function saveGrid() {
    try {
      const res = await api.saveGrid(gridData, filename || undefined);
      if (res.success) {
        filename = res.filename;
        appState.addToast(`Grid saved to ${res.filename}`, "success");
      }
    } catch (e) {
      appState.addToast(`Failed to save grid: ${e}`, "error");
    }
  }

  async function restoreToUnity() {
    try {
      if (!filename) return;
      await api.restoreGrid(filename);
      appState.addToast("Restore command sent to Unity", "success");
    } catch (e) {
      appState.addToast(`Restore failed: ${e}`, "error");
    }
  }

  function setCellColor(index: number) {
    gridData[index].color = selectedColor;
  }

  // Calculate grid dimensions
  let maxGridX = $derived(Math.max(...gridData.map((p) => p.gridX), 0));
  let maxGridY = $derived(Math.max(...gridData.map((p) => p.gridY), 0));

  onMount(() => {
    loadGrid();
  });
</script>

<div class="grid-editor">
  <div class="toolbar">
    <div class="color-palette">
      {#each colors as color}
        <button
          class="color-btn"
          class:active={selectedColor === color.id}
          style="--color: {color.hex}"
          onclick={() => (selectedColor = color.id)}
          title={color.label}
        >
          <span class="label">{color.label}</span>
        </button>
      {/each}
    </div>
    <div class="actions">
      <button class="btn" onclick={loadGrid}>Reload</button>
      <button class="btn primary" onclick={saveGrid}>Save Grid</button>
      <button class="btn" onclick={restoreToUnity} disabled={!filename}
        >Restore Unity</button
      >
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading grid data...</div>
  {:else if gridData.length === 0}
    <div class="empty">No grid data found.</div>
  {:else}
    <div
      class="grid-container"
      style="--cols: {maxGridX + 1}; --rows: {maxGridY + 1}"
    >
      {#each gridData as point, i}
        <button
          class="grid-cell"
          style="grid-column: {point.gridX + 1}; grid-row: {point.gridY +
            1}; --cell-color: {colors.find((c) => c.id === point.color)?.hex ||
            '#475569'}"
          onclick={() => setCellColor(i)}
        >
          <span class="coord">({point.gridX}, {point.gridY})</span>
          <span class="color-label">{point.color}</span>
        </button>
      {/each}
    </div>
  {/if}

  <div class="info">
    <p>Filename: <code>{filename}</code></p>
    <p>
      Tip: Select a color from the top, then click on grid cells to apply that
      color.
    </p>
  </div>
</div>

<style>
  .grid-editor {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 16px;
    background: #111827;
    border-radius: 12px;
    border: 1px solid #1f2937;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .color-palette {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .color-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border: 2px solid transparent;
    border-radius: 6px;
    background: #1f2937;
    color: #f3f4f6;
    cursor: pointer;
    transition: all 0.2s;
  }

  .color-btn::before {
    content: "";
    display: block;
    width: 14px;
    height: 14px;
    border-radius: 2px;
    background: var(--color);
  }

  .color-btn.active {
    border-color: #38bdf8;
    background: #374151;
  }

  .color-btn:hover {
    background: #374151;
  }

  .color-btn .label {
    font-size: 0.8rem;
    font-weight: 500;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .btn {
    padding: 8px 16px;
    border: 1px solid #374151;
    border-radius: 6px;
    background: #1f2937;
    color: #f3f4f6;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn:hover:not(:disabled) {
    background: #374151;
    border-color: #4b5563;
  }

  .btn.primary {
    background: #2563eb;
    border-color: #3b82f6;
  }

  .btn.primary:hover {
    background: #3b82f6;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .grid-container {
    display: grid;
    grid-template-columns: repeat(var(--cols), 1fr);
    grid-template-rows: repeat(var(--rows), 1fr);
    gap: 12px;
    max-width: 600px;
    margin: 0 auto;
    background: #1f2937;
    padding: 16px;
    border-radius: 8px;
    aspect-ratio: 1 / 1;
  }

  .grid-cell {
    aspect-ratio: 1 / 1;
    border: none;
    border-radius: 6px;
    background: var(--cell-color);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
    transition:
      transform 0.1s,
      filter 0.2s;
    overflow: hidden;
  }

  .grid-cell:hover {
    transform: scale(1.03);
    filter: brightness(1.1);
  }

  .grid-cell:active {
    transform: scale(0.97);
  }

  .coord {
    font-size: 0.65rem;
    opacity: 0.8;
  }

  .color-label {
    font-size: 0.75rem;
    font-weight: bold;
    text-transform: capitalize;
  }

  .loading,
  .empty {
    padding: 40px;
    text-align: center;
    color: #9ca3af;
    background: #1f2937;
    border-radius: 8px;
  }

  .info {
    font-size: 0.8rem;
    color: #9ca3af;
    border-top: 1px solid #1f2937;
    padding-top: 12px;
  }

  code {
    background: #374151;
    padding: 2px 6px;
    border-radius: 4px;
    color: #e5e7eb;
  }
</style>
