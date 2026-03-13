<script lang="ts">
  let {
    onAccept,
    onReject,
  }: {
    onAccept: () => void;
    onReject: (reason: string) => void;
  } = $props();

  let rejectText = $state('');

  function reject() {
    onReject(rejectText.trim() || 'No');
    rejectText = '';
  }
</script>

<div class="confirmation">
  <p class="prompt">Please confirm the selection result:</p>
  <div class="actions">
    <button class="btn accept" onclick={onAccept}>✅ Accept (Yes)</button>
    <div class="reject-group">
      <input
        type="text"
        bind:value={rejectText}
        placeholder="Rephrase / Reason (optional)"
        onkeydown={(e) => e.key === 'Enter' && reject()}
      />
      <button class="btn reject" onclick={reject}>❌ Reject</button>
    </div>
  </div>
</div>

<style>
  .confirmation {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #fbbf24;
  }
  .prompt {
    margin: 0 0 12px;
    color: #fbbf24;
    font-size: 0.85rem;
    font-weight: 600;
  }
  .actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .reject-group {
    display: flex;
    gap: 8px;
  }
  .reject-group input {
    flex: 1;
    padding: 8px 12px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 0.8rem;
  }
  .reject-group input:focus {
    outline: none;
    border-color: #38bdf8;
  }
  .btn {
    padding: 8px 20px;
    border: none;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn.accept {
    background: #0d3320;
    color: #4ade80;
    border: 1px solid #166534;
  }
  .btn.accept:hover {
    background: #166534;
  }
  .btn.reject {
    background: #3b1c1c;
    color: #f87171;
    border: 1px solid #7f1d1d;
    white-space: nowrap;
  }
  .btn.reject:hover {
    background: #7f1d1d;
  }
</style>
