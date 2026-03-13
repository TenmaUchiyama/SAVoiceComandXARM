<script lang="ts">
  let { onSubmit }: { onSubmit: (text: string) => void } = $props();

  let text = $state('');

  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    text = '';
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }
</script>

<div class="input-row">
  <input
    type="text"
    bind:value={text}
    onkeydown={handleKeydown}
    placeholder="Enter utterance (e.g. take the red object on the right)"
  />
  <button class="btn" onclick={submit} disabled={!text.trim()}>Send</button>
</div>

<style>
  .input-row {
    display: flex;
    gap: 8px;
  }
  input {
    flex: 1;
    padding: 10px 14px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    font-size: 0.9rem;
  }
  input:focus {
    outline: none;
    border-color: #38bdf8;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
  }
  input::placeholder {
    color: #475569;
  }
  .btn {
    padding: 10px 24px;
    border: none;
    border-radius: 6px;
    background: #2563eb;
    color: #fff;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .btn:hover:not(:disabled) {
    background: #3b82f6;
  }
  .btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
</style>
