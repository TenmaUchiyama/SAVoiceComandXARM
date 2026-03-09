<script lang="ts">
  let { children } = $props();
</script>

<svelte:head>
  <title>InteractionApp</title>
  <meta name="description" content="Spatially Aware Robot Arm - Interaction App" />
</svelte:head>

{@render children()}
