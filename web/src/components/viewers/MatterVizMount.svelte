<script lang="ts">
  import { Structure } from 'matterviz/structure'

  let { cifText }: { cifText: string } = $props()
</script>

<svelte:boundary>
  <Structure
    source={{ data: cifText, filename: 'structure.cif' }}
    allow_file_drop={false}
    persist_settings={false}
    show_host_tool={false}
    style="--struct-width:100%; --struct-height:100%; --struct-min-width:0; --struct-max-width:100%"
  />
  {#snippet failed(error)}
    <div role="alert" style="padding:16px;color:#b91c1c;overflow:auto">
      MatterViz could not render this CIF: {error instanceof Error ? error.message : String(error)}
    </div>
  {/snippet}
</svelte:boundary>
