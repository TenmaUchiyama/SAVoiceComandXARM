<script lang="ts">
  import type { SpatialReferenceResult } from '$lib/types';

  let { result }: { result: SpatialReferenceResult } = $props();
</script>

<div class="result-card">
  <div class="top-section">
    <div class="main-result">
      <span class="label">Top Candidate</span>
      <span class="value">{result.top_candidate_id}</span>
    </div>
    <div class="confidence" class:high={result.confidence >= 0.7} class:medium={result.confidence >= 0.4 && result.confidence < 0.7} class:low={result.confidence < 0.4}>
      <span class="label">Confidence</span>
      <span class="value">{(result.confidence * 100).toFixed(1)}%</span>
    </div>
  </div>

  {#if result.reasoning}
    <div class="reasoning">
      <span class="label">Reasoning</span>
      <p>{result.reasoning}</p>
    </div>
  {/if}

  {#if result.candidates && result.candidates.length > 0}
    <div class="candidates">
      <span class="label">Candidates</span>
      <table>
        <thead>
          <tr>
            <th>Object ID</th>
            <th>Score</th>
            <th>Reasoning</th>
          </tr>
        </thead>
        <tbody>
          {#each result.candidates as c}
            <tr class:top={c.object_id === result.top_candidate_id}>
              <td class="id-cell">{c.object_id}</td>
              <td class="score-cell">{(c.score * 100).toFixed(1)}%</td>
              <td class="reason-cell">{c.reasoning}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .result-card {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #334155;
  }
  .top-section {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .main-result .value {
    font-size: 1.2rem;
    font-weight: 700;
    color: #38bdf8;
  }
  .confidence .value {
    font-size: 1.2rem;
    font-weight: 700;
  }
  .confidence.high .value { color: #4ade80; }
  .confidence.medium .value { color: #fbbf24; }
  .confidence.low .value { color: #f87171; }
  .label {
    display: block;
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 2px;
  }
  .reasoning {
    margin-bottom: 12px;
    padding: 10px;
    background: #0f172a;
    border-radius: 6px;
  }
  .reasoning p {
    margin: 4px 0 0;
    color: #cbd5e1;
    font-size: 0.85rem;
    line-height: 1.5;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }
  th {
    text-align: left;
    padding: 6px 8px;
    color: #64748b;
    border-bottom: 1px solid #334155;
    font-weight: 600;
  }
  td {
    padding: 6px 8px;
    color: #cbd5e1;
    border-bottom: 1px solid #1e293b;
  }
  tr.top {
    background: rgba(56, 189, 248, 0.08);
  }
  .id-cell {
    font-family: monospace;
    color: #38bdf8;
  }
  .score-cell {
    font-weight: 600;
  }
  .reason-cell {
    font-size: 0.75rem;
    color: #94a3b8;
    max-width: 300px;
  }
</style>
