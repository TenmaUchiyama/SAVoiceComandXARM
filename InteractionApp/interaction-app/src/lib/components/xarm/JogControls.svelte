<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { appState, wsRobot } from '$lib/appState.svelte';
  import type { JogAxis } from '$lib/types';

  // Step size (mm per loop iteration, equivalent to STEP_MM in keyboard_move.py)
  let stepMm = $state(4);

  let jogging = $state<JogAxis | ''>('');

  // Reflect final position on jog_stopped event
  function onJogStopped(data: unknown) {
    const d = data as { success: boolean; position?: number[] };
    if (d.position && appState.robotStatus) {
      appState.robotStatus = { ...appState.robotStatus, position: d.position };
    }
  }

  // Notify error on jog_started
  function onJogStarted(data: unknown) {
    const d = data as { success: boolean; message?: string };
    if (!d.success) {
      appState.addToast(`Jog failed: ${d.message ?? ''}`, 'error');
      jogging = '';
    }
  }

  onMount(() => {
    wsRobot.on('jog_started', onJogStarted);
    wsRobot.on('jog_stopped', onJogStopped);
  });

  onDestroy(() => {
    wsRobot.off('jog_started', onJogStarted);
    wsRobot.off('jog_stopped', onJogStopped);
    // Stop safely when component is destroyed
    if (jogging) {
      wsRobot.send('jog_stop', {});
      jogging = '';
    }
  });

  function beginJog(axis: JogAxis, event?: PointerEvent) {
    event?.preventDefault();
    if (event?.currentTarget instanceof HTMLElement) {
      event.currentTarget.setPointerCapture?.(event.pointerId);
    }
    if (jogging === axis) return;
    if (jogging) stopJog();

    if (!wsRobot.connected) {
      appState.addToast('Robot WS not connected', 'error');
      return;
    }

    jogging = axis;
    wsRobot.send('jog_start', { axis, step_mm: stepMm });
  }

  function stopJog(axis?: JogAxis) {
    if (axis && jogging !== axis) return;
    if (!jogging) return;
    jogging = '';
    wsRobot.send('jog_stop', {});
  }

  function handleKeydown(event: KeyboardEvent, axis: JogAxis) {
    if (event.repeat) return;
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      beginJog(axis);
    }
  }

  function handleKeyup(event: KeyboardEvent, axis: JogAxis) {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      stopJog(axis);
    }
  }

  function isDisabled(axis: JogAxis) {
    return jogging !== '' && jogging !== axis;
  }
</script>

<section class="panel">
  <h3>Jog Controls</h3>

  <div class="distance-row">
    <span class="label">Step (mm)</span>
    <div class="distance-btns">
      {#each [1, 2, 4, 8, 16] as d}
        <button
          class="dist-btn"
          class:active={stepMm === d}
          onclick={() => (stepMm = d)}
        >
          {d}
        </button>
      {/each}
    </div>
  </div>

  <p class="hint">Moves continuously by {stepMm}mm every 30ms while held.</p>

  {#if !wsRobot.connected}
    <p class="ws-warn">Robot WS disconnected — reconnecting…</p>
  {/if}

  <div class="jog-grid">
    <!-- Top row: X+ (same as up in keyboard_move.py) -->
    <div class="jog-cell"></div>
    <button
      class="jog-btn"
      class:active={jogging === 'x'}
      disabled={isDisabled('x')}
      onpointerdown={(e) => beginJog('x', e)}
      onpointerup={() => stopJog('x')}
      onpointercancel={() => stopJog('x')}
      onlostpointercapture={() => stopJog('x')}
      onkeydown={(e) => handleKeydown(e, 'x')}
      onkeyup={(e) => handleKeyup(e, 'x')}
      onblur={() => stopJog('x')}
    >X+</button>
    <div class="jog-cell"></div>
    <div class="jog-cell"></div>
    <button
      class="jog-btn z-btn"
      class:active={jogging === 'z'}
      disabled={isDisabled('z')}
      onpointerdown={(e) => beginJog('z', e)}
      onpointerup={() => stopJog('z')}
      onpointercancel={() => stopJog('z')}
      onlostpointercapture={() => stopJog('z')}
      onkeydown={(e) => handleKeydown(e, 'z')}
      onkeyup={(e) => handleKeyup(e, 'z')}
      onblur={() => stopJog('z')}
    >Z+</button>

    <!-- Middle row: Y-, Y+ (same as left/right in keyboard_move.py) -->
    <button
      class="jog-btn"
      class:active={jogging === '-y'}
      disabled={isDisabled('-y')}
      onpointerdown={(e) => beginJog('-y', e)}
      onpointerup={() => stopJog('-y')}
      onpointercancel={() => stopJog('-y')}
      onlostpointercapture={() => stopJog('-y')}
      onkeydown={(e) => handleKeydown(e, '-y')}
      onkeyup={(e) => handleKeyup(e, '-y')}
      onblur={() => stopJog('-y')}
    >Y-</button>
    <div class="jog-center">{stepMm}mm</div>
    <button
      class="jog-btn"
      class:active={jogging === 'y'}
      disabled={isDisabled('y')}
      onpointerdown={(e) => beginJog('y', e)}
      onpointerup={() => stopJog('y')}
      onpointercancel={() => stopJog('y')}
      onlostpointercapture={() => stopJog('y')}
      onkeydown={(e) => handleKeydown(e, 'y')}
      onkeyup={(e) => handleKeyup(e, 'y')}
      onblur={() => stopJog('y')}
    >Y+</button>
    <div class="jog-cell"></div>
    <div class="jog-cell"></div>

    <!-- Bottom row: X- -->
    <div class="jog-cell"></div>
    <button
      class="jog-btn"
      class:active={jogging === '-x'}
      disabled={isDisabled('-x')}
      onpointerdown={(e) => beginJog('-x', e)}
      onpointerup={() => stopJog('-x')}
      onpointercancel={() => stopJog('-x')}
      onlostpointercapture={() => stopJog('-x')}
      onkeydown={(e) => handleKeydown(e, '-x')}
      onkeyup={(e) => handleKeyup(e, '-x')}
      onblur={() => stopJog('-x')}
    >X-</button>
    <div class="jog-cell"></div>
    <div class="jog-cell"></div>
    <button
      class="jog-btn z-btn"
      class:active={jogging === '-z'}
      disabled={isDisabled('-z')}
      onpointerdown={(e) => beginJog('-z', e)}
      onpointerup={() => stopJog('-z')}
      onpointercancel={() => stopJog('-z')}
      onlostpointercapture={() => stopJog('-z')}
      onkeydown={(e) => handleKeydown(e, '-z')}
      onkeyup={(e) => handleKeyup(e, '-z')}
      onblur={() => stopJog('-z')}
    >Z-</button>
  </div>

  {#if appState.robotStatus?.position}
    <div class="position-display">
      <span class="pos-label">Position:</span>
      <span class="pos-val">
        X:{appState.robotStatus.position[0]?.toFixed(1)}
        Y:{appState.robotStatus.position[1]?.toFixed(1)}
        Z:{appState.robotStatus.position[2]?.toFixed(1)}
      </span>
    </div>
  {/if}
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
  .distance-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
  }
  .hint {
    margin: 0 0 8px;
    font-size: 0.72rem;
    color: #64748b;
  }
  .ws-warn {
    margin: 0 0 8px;
    font-size: 0.72rem;
    color: #f59e0b;
  }
  .label {
    font-size: 0.75rem;
    color: #64748b;
    white-space: nowrap;
  }
  .distance-btns {
    display: flex;
    gap: 4px;
  }
  .dist-btn {
    padding: 4px 10px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #0f172a;
    color: #94a3b8;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .dist-btn:hover {
    background: #334155;
  }
  .dist-btn.active {
    background: #1e3a5f;
    color: #38bdf8;
    border-color: #2563eb;
  }

  .jog-grid {
    display: grid;
    grid-template-columns: 56px 56px 56px 16px 56px;
    grid-template-rows: 48px 48px 48px;
    gap: 4px;
    justify-content: center;
  }
  .jog-cell {
    min-width: 0;
  }
  .jog-btn {
    border: 1px solid #334155;
    border-radius: 6px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.1s, border-color 0.1s;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
    touch-action: none;
  }
  .jog-btn:hover:not(:disabled) {
    background: #334155;
    border-color: #475569;
  }
  .jog-btn.active {
    background: #2563eb;
    border-color: #3b82f6;
    color: #fff;
  }
  .jog-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .jog-btn.z-btn {
    background: #1a1a2e;
    border-color: #4c1d95;
    color: #c4b5fd;
  }
  .jog-btn.z-btn:hover:not(:disabled) {
    background: #4c1d95;
    color: #fff;
  }
  .jog-btn.z-btn.active {
    background: #7c3aed;
    border-color: #8b5cf6;
    color: #fff;
  }
  .jog-center {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    color: #475569;
    border: 1px dashed #334155;
    border-radius: 6px;
  }

  .position-display {
    margin-top: 12px;
    padding: 8px 12px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.75rem;
  }
  .pos-label {
    color: #64748b;
  }
  .pos-val {
    color: #38bdf8;
    margin-left: 4px;
  }
</style>
