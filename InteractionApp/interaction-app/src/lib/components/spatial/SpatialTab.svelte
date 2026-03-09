<script lang="ts">
  import type {
    SpatialReferenceResult,
    RobotCommand,
    SceneObject,
  } from '$lib/types';
  import { appState, wsSpatial } from '$lib/appState.svelte';
  import { generateRequestId } from '$lib/ws.svelte';
  import StatusBadge from '../StatusBadge.svelte';
  import UtteranceInput from './UtteranceInput.svelte';
  import ResultCard from './ResultCard.svelte';
  import ConfirmationPanel from './ConfirmationPanel.svelte';
  import ObjectTable from './ObjectTable.svelte';

  // Demo objects for testing
  let objects = $state<SceneObject[]>([
    { id: 'obj_00', label: 'Red Cube', color: 'red', position: { x: 0.5, y: 0, z: 1.0 } },
    { id: 'obj_01', label: 'Blue Sphere', color: 'blue', position: { x: -0.3, y: 0, z: 0.8 } },
    { id: 'obj_02', label: 'Green Cylinder', color: 'green', position: { x: 0.1, y: 0, z: 1.5 } },
  ]);

  let robotCommandStatus = $state<RobotCommand | null>(null);

  // Phase labels
  const phaseLabels: Record<string, string> = {
    idle: '待機中',
    processing: '処理中...',
    showing_result: '結果表示',
    awaiting_confirmation: '確認待ち',
    executing: 'ロボット実行中',
  };

  function sendUtterance(text: string) {
    const reqId = generateRequestId('spatial');
    appState.lastRequestId = reqId;
    appState.spatialPhase = 'processing';
    appState.lastResult = null;
    robotCommandStatus = null;

    wsSpatial.send('spatial_reference_request', {
      request_id: reqId,
      utterance: { text, language: 'ja' },
      user_pose: {
        position: { x: 0, y: 1.5, z: 0 },
        forward: { x: 0, y: 0, z: 1 },
        up: { x: 0, y: 1, z: 0 },
      },
      objects: objects,
    });
  }

  function handleAccept() {
    if (!appState.lastResult) return;
    const reqId = generateRequestId('confirm');
    appState.spatialPhase = 'executing';

    wsSpatial.send('confirmation', {
      request_id: reqId,
      original_request_id: appState.lastRequestId,
      confirmed_object_id: appState.lastResult.top_candidate_id,
      action: 'pick',
      accepted: true,
    });
  }

  function handleReject(reason: string) {
    if (!appState.lastResult) return;
    const reqId = generateRequestId('confirm_interpret');
    appState.spatialPhase = 'processing';

    wsSpatial.send('confirmation_interpretation_request', {
      request_id: reqId,
      original_request_id: appState.lastRequestId,
      utterance: { text: reason, language: 'ja' },
      confirmed_object_id: appState.lastResult.top_candidate_id,
      action: 'pick',
    });
  }

  // Listen for results
  wsSpatial.on('spatial_reference_result', (data: unknown) => {
    const result = data as SpatialReferenceResult;
    appState.lastResult = result;
    appState.lastTargetId = result.top_candidate_id;
    appState.spatialPhase = 'showing_result';
  });

  wsSpatial.on('robot_command', (data: unknown) => {
    const cmd = data as RobotCommand;
    robotCommandStatus = cmd;
    if (cmd.status === 'completed' || cmd.status === 'failed') {
      appState.spatialPhase = 'idle';
      if (cmd.status === 'completed') {
        appState.addToast(`Robot command completed: ${cmd.action} → ${cmd.target_object_id}`, 'success');
      } else {
        appState.addToast(`Robot command failed: ${cmd.message}`, 'error');
      }
    } else {
      appState.spatialPhase = 'executing';
    }
  });

  wsSpatial.on('error', (data: unknown) => {
    const err = data as { code?: string; message: string };
    appState.spatialPhase = 'idle';
    appState.addToast(`Error ${err.code ?? ''}: ${err.message}`, 'error');
  });
</script>

<div class="spatial-tab">
  <div class="status-bar">
    <StatusBadge connected={wsSpatial.connected} label="Spatial WS" />
    <span class="phase-badge phase-{appState.spatialPhase}">
      {phaseLabels[appState.spatialPhase] ?? appState.spatialPhase}
    </span>
  </div>

  <!-- Utterance input -->
  <UtteranceInput onSubmit={sendUtterance} />

  <!-- Robot command status -->
  {#if robotCommandStatus}
    <div class="robot-status" class:started={robotCommandStatus.status === 'started'} class:completed={robotCommandStatus.status === 'completed'} class:failed={robotCommandStatus.status === 'failed'}>
      <span class="status-icon">
        {#if robotCommandStatus.status === 'started'}⏳
        {:else if robotCommandStatus.status === 'completed'}✅
        {:else}❌{/if}
      </span>
      Robot: {robotCommandStatus.action} → {robotCommandStatus.target_object_id}
      ({robotCommandStatus.status})
      {#if robotCommandStatus.message}
        <span class="status-msg">— {robotCommandStatus.message}</span>
      {/if}
    </div>
  {/if}

  <!-- Result -->
  {#if appState.lastResult}
    <ResultCard result={appState.lastResult} />
  {/if}

  <!-- Confirmation -->
  {#if appState.spatialPhase === 'showing_result' && appState.lastResult}
    <ConfirmationPanel onAccept={handleAccept} onReject={handleReject} />
  {/if}

  <!-- Object table -->
  <ObjectTable {objects} />
</div>

<style>
  .spatial-tab {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .status-bar {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .phase-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .phase-idle {
    background: #1e293b;
    color: #94a3b8;
  }
  .phase-processing {
    background: #1e3a5f;
    color: #38bdf8;
    animation: pulse 1.5s ease-in-out infinite;
  }
  .phase-showing_result {
    background: #1a2e05;
    color: #a3e635;
  }
  .phase-awaiting_confirmation {
    background: #422006;
    color: #fbbf24;
  }
  .phase-executing {
    background: #3b0764;
    color: #c084fc;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }
  .robot-status {
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .robot-status.started {
    background: #1e3a5f;
    color: #38bdf8;
    border: 1px solid #2563eb;
  }
  .robot-status.completed {
    background: #0d3320;
    color: #4ade80;
    border: 1px solid #166534;
  }
  .robot-status.failed {
    background: #3b1c1c;
    color: #f87171;
    border: 1px solid #7f1d1d;
  }
  .status-icon {
    font-size: 1.1rem;
  }
  .status-msg {
    color: #94a3b8;
    font-size: 0.8rem;
  }
</style>
