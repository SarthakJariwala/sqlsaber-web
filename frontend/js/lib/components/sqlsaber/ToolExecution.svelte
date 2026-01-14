<script lang="ts">
  import { cn } from "$lib/utils";
  import ChevronRightIcon from "@lucide/svelte/icons/chevron-right";
  import CheckCircleIcon from "@lucide/svelte/icons/check-circle";
  import LoaderIcon from "@lucide/svelte/icons/loader";
  import { slide } from "svelte/transition";
  import { Response } from "$lib/components/ai-elements/response";
  import { Shimmer } from "$lib/components/ai-elements/shimmer";
  import * as Code from "$lib/components/ai-elements/code";
  import {
    getToolDisplayName,
    parseToolArgs,
    parseToolResult,
    formatSqlResultsAsMarkdown,
    formatSchemaAsMarkdown,
    formatTableListAsMarkdown,
    type SqlResult,
    type IntrospectSchemaResult,
    type ListTablesResult,
  } from "./tool-utils";

  interface Props {
    toolName: string;
    args?: unknown; // Can be string (JSON) or object
    result?: unknown; // Can be string (JSON) or object
    class?: string;
  }

  let { toolName, args, result, class: className }: Props = $props();

  let expanded = $state(false);
  let hasResult = $derived(result !== undefined && result !== null);
  let status = $derived<"pending" | "complete">(
    hasResult ? "complete" : "pending"
  );
  let displayName = $derived(getToolDisplayName(toolName, status));

  let parsedArgs = $derived(parseToolArgs(args));
  let parsedResult = $derived(parseToolResult(result));

  function toggle() {
    expanded = !expanded;
  }

  // Get the SQL query from args if this is execute_sql
  let sqlQuery = $derived(
    toolName === "execute_sql" && parsedArgs.query
      ? String(parsedArgs.query)
      : null
  );

  // Get the table pattern from args if this is introspect_schema
  let tablePattern = $derived(
    toolName === "introspect_schema" && parsedArgs.table_pattern
      ? String(parsedArgs.table_pattern)
      : null
  );

  // Format result based on tool type
  let formattedResult = $derived.by(() => {
    if (!hasResult || !parsedResult) return null;

    switch (toolName) {
      case "execute_sql":
        return formatSqlResultsAsMarkdown(parsedResult as SqlResult);
      case "introspect_schema":
        return formatSchemaAsMarkdown(parsedResult as IntrospectSchemaResult);
      case "list_tables":
        return formatTableListAsMarkdown(parsedResult as ListTablesResult);
      default:
        // Fallback: show as formatted JSON
        return "```json\n" + JSON.stringify(parsedResult, null, 2) + "\n```";
    }
  });
</script>

<div class={cn("rounded-lg border bg-card", className)}>
  <button
    type="button"
    onclick={toggle}
    class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors"
  >
    <ChevronRightIcon
      class={cn(
        "size-4 text-muted-foreground transition-transform shrink-0",
        expanded && "rotate-90"
      )}
    />

    {#if status === "complete"}
      <CheckCircleIcon class="size-4 text-green-500 shrink-0" />
      <span class="text-sm font-medium">{displayName}</span>
    {:else}
      <LoaderIcon class="size-4 text-muted-foreground animate-spin shrink-0" />
      <Shimmer as="span" content_length={20} class="text-sm font-medium"
        >{displayName}</Shimmer
      >
    {/if}

    {#if tablePattern}
      <span class="text-sm text-muted-foreground">
        — <code class="bg-muted px-1 py-0.5 rounded text-xs"
          >{tablePattern}</code
        >
      </span>
    {/if}
  </button>

  {#if expanded}
    <div
      transition:slide={{ duration: 200 }}
      class="border-t px-4 py-3 space-y-4"
    >
      {#if sqlQuery}
        <div>
          <div class="text-xs font-medium text-muted-foreground mb-2">
            Query
          </div>
          <Code.Root lang="sql" code={sqlQuery} hideLines>
            <Code.CopyButton />
          </Code.Root>
        </div>
      {/if}

      {#if formattedResult}
        <div>
          {#if sqlQuery}
            <div class="text-xs font-medium text-muted-foreground mb-2">
              Results
            </div>
          {/if}
          <div class="prose prose-sm dark:prose-invert max-w-none">
            <Response content={formattedResult} />
          </div>
        </div>
      {/if}

      {#if !sqlQuery && !formattedResult && !hasResult}
        <div class="space-y-2">
          <Shimmer content_length={30}>Executing tool...</Shimmer>
        </div>
      {/if}
    </div>
  {/if}
</div>
