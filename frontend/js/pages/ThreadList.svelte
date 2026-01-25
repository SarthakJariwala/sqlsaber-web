<script lang="ts">
  import { Link, router } from "@inertiajs/svelte";
  import { Plus, Settings } from "@lucide/svelte";
  import { Badge } from "$lib/components/ui/badge";
  import { Button } from "$lib/components/ui/button";
  import {
    Pagination,
    PaginationContent,
    PaginationItem,
    PaginationLink,
    PaginationEllipsis,
    PaginationNext,
    PaginationPrevious,
  } from "$lib/components/ui/pagination";
  import {
    type ThreadSummary,
    formatThreadDate,
    STATUS_BADGE_STYLES,
  } from "$lib/types/thread";

  type PaginationMeta = {
    count: number;
    perPage: number;
    page: number;
  };

  interface Props {
    threads: ThreadSummary[];
    pagination: PaginationMeta;
  }

  let { threads, pagination }: Props = $props();

  let loading = $state(false);
  let error = $state<string | null>(null);

  function handlePageChange(nextPage: number) {
    if (nextPage === pagination.page) return;
    router.get(
      "/threads/",
      { page: nextPage },
      { preserveScroll: true, preserveState: true }
    );
  }
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
              <Badge class={STATUS_BADGE_STYLES[thread.status]}>
                {thread.status}
              </Badge>
            </div>
          </Link>
        {/each}
      </div>
      {#if pagination && pagination.count > pagination.perPage}
        <div class="mx-auto max-w-3xl border-t px-4 py-4">
          <Pagination
            count={pagination.count}
            perPage={pagination.perPage}
            page={pagination.page}
            siblingCount={1}
            onPageChange={handlePageChange}
          >
            {#snippet child({ props, pages, currentPage })}
              <nav {...props}>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious />
                  </PaginationItem>
                  {#each pages as pageItem (pageItem.key)}
                    {#if pageItem.type === "ellipsis"}
                      <PaginationItem>
                        <PaginationEllipsis />
                      </PaginationItem>
                    {:else}
                      <PaginationItem>
                        <PaginationLink
                          page={pageItem}
                          isActive={currentPage === pageItem.value}
                        />
                      </PaginationItem>
                    {/if}
                  {/each}
                  <PaginationItem>
                    <PaginationNext />
                  </PaginationItem>
                </PaginationContent>
              </nav>
            {/snippet}
          </Pagination>
        </div>
      {/if}
    {/if}
  </div>
</div>
