<script lang="ts">
  import { Link } from "@inertiajs/svelte";
  import { Plus, Settings } from "@lucide/svelte";
  import { Button } from "$lib/components/ui/button";
  import {
    type ThreadSummary,
    formatThreadDate,
    STATUS_BADGE_STYLES,
  } from "$lib/types/thread";

  interface Props {
    threads: ThreadSummary[];
  }

  let { threads }: Props = $props();

  let loading = $state(false);
  let error = $state<string | null>(null);
</script>

<div class="flex h-screen flex-col">
  <!-- Header -->
  <header class="flex items-center justify-between border-b px-4 py-3">
    <h1 class="text-lg font-semibold">Threads</h1>
    <div class="flex items-center gap-3">
      <Link href="/">
        <Button>
          <Plus class="h-4 w-4" />
          New Thread
        </Button>
      </Link>
      <Link
        href="/settings/"
        class="text-muted-foreground transition-colors hover:text-foreground"
        aria-label="Settings"
      >
        <Settings class="h-5 w-5" />
      </Link>
    </div>
  </header>

  <!-- Thread List -->
  <div class="flex-1 overflow-y-auto">
    {#if loading}
      <div class="flex h-full items-center justify-center">
        <p class="text-muted-foreground">Loading threads...</p>
      </div>
    {:else if error}
      <div class="flex h-full items-center justify-center">
        <p class="text-red-500">{error}</p>
      </div>
    {:else if threads.length === 0}
      <div class="flex h-full flex-col items-center justify-center gap-4">
        <p class="text-muted-foreground">No threads yet</p>
        <Link href="/">
          <Button>
            <Plus class="h-4 w-4" />
            Start your first conversation
          </Button>
        </Link>
      </div>
    {:else}
      <div class="mx-auto max-w-3xl divide-y">
        {#each threads as thread (thread.id)}
          <Link
            href={`/threads/${thread.id}/`}
            class="block px-4 py-4 transition-colors hover:bg-accent"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0 flex-1">
                <h2 class="truncate font-medium">
                  {thread.title || "Untitled thread"}
                </h2>
                <p class="mt-1 text-sm text-muted-foreground">
                  {formatThreadDate(thread.updated_at)}
                </p>
              </div>
              <span
                class="rounded-full px-2 py-1 text-xs font-medium {STATUS_BADGE_STYLES[
                  thread.status
                ]}"
              >
                {thread.status}
              </span>
            </div>
          </Link>
        {/each}
      </div>
    {/if}
  </div>
</div>
