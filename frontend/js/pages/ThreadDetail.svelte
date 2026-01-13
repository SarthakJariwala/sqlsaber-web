<script lang="ts">
  import { Link, router } from "@inertiajs/svelte";
  import axios from "axios";
  import { ChevronLeft, Settings } from "@lucide/svelte";

  import {
    Message,
    MessageContent,
    MessageResponse,
  } from "$lib/components/ai-elements/new-message";

  import { ThinkingBlock, ToolExecution } from "$lib/components/sqlsaber";
  import { Shimmer } from "$lib/components/ai-elements/shimmer";

  import {
    PromptInput,
    PromptInputBody,
    PromptInputTextarea,
    PromptInputToolbar,
    PromptInputSubmit,
    PromptInputModelSelect,
    PromptInputModelSelectTrigger,
    PromptInputModelSelectContent,
    PromptInputModelSelectItem,
    PromptInputModelSelectValue,
    type PromptInputMessage,
  } from "$lib/components/ai-elements/prompt-input";

  import {
    getDisplayItemKey,
    mergeToolMessages,
    selectActiveIdOrDefault,
    type DatabaseConnection,
    type ModelConfig,
    type ThreadData,
    type MessageData,
  } from "$lib/types/thread";
  import { useThreadPolling } from "$lib/hooks/use-thread-polling.svelte";

  interface Props {
    thread: ThreadData;
    messages: MessageData[];
    configured: boolean;
    defaults: {
      database_connection_id: number | null;
      model_config_id: number | null;
    };
    database_connections: DatabaseConnection[];
    model_configs: ModelConfig[];
  }
  let props: Props = $props();

  // Redirect if not configured
  if (!props.configured) {
    router.visit("/settings/");
  }

  const polling = useThreadPolling(props.thread, props.messages);

  let messagesContainer: HTMLDivElement | null = null;

  let loading = $state(false);
  let configLoading = $state(false);

  let databaseConnections = $state<DatabaseConnection[]>(props.database_connections);
  let modelConfigs = $state<ModelConfig[]>(props.model_configs);

  let activeDatabaseConnections = $derived(
    databaseConnections.filter((d) => d.is_active)
  );
  let activeModelConfigs = $derived(
    modelConfigs.filter((m) => m.is_active && m.api_key_is_active)
  );

  let selectedDatabaseId = $state(
    selectActiveIdOrDefault(
      props.thread.database_connection_id,
      props.thread.database_connection_is_active,
      props.defaults.database_connection_id
    )
  );
  let selectedModelId = $state(
    selectActiveIdOrDefault(
      props.thread.model_config_id,
      props.thread.model_config_is_active,
      props.defaults.model_config_id
    )
  );

  let selectedDatabaseLabel = $derived(
    activeDatabaseConnections.find((d) => String(d.id) === selectedDatabaseId)
      ?.name ?? ""
  );

  let selectedModelLabel = $derived(
    activeModelConfigs.find((m) => String(m.id) === selectedModelId)
      ?.display_name ?? ""
  );

  let controlsDisabled = $derived(!polling.canSubmit || configLoading);

  let sendDisabled = $derived(
    !polling.canSubmit ||
      configLoading ||
      selectedDatabaseId === "" ||
      selectedModelId === ""
  );

  let displayMessages = $derived(mergeToolMessages(polling.messages));

  $effect(() => {
    if (polling.messages.length > 0 && messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  });

  async function handleSubmit(message: PromptInputMessage) {
    const prompt = message.text?.trim();
    if (!prompt || !polling.thread) return;

    polling.setChatStatus("submitted");

    try {
      await axios.post(`/api/threads/${polling.thread.id}/continue/`, {
        prompt,
        database_connection_id: selectedDatabaseId
          ? Number(selectedDatabaseId)
          : null,
        model_config_id: selectedModelId ? Number(selectedModelId) : null,
      });

      polling.setRunning();
      polling.addTempUserMessage(prompt);
      polling.start();
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const redirect = (error.response?.data as { redirect?: string } | undefined)
          ?.redirect;
        if (redirect) {
          router.visit(redirect);
          return;
        }
      }

      console.error("Submit error:", error);
      polling.setChatStatus("error");
    }
  }
</script>

<div class="flex h-screen flex-col">
  <header class="flex items-center gap-4 border-b px-4 py-3">
    <Link
      href="/threads/"
      class="text-muted-foreground transition-colors hover:text-foreground"
    >
      <ChevronLeft class="h-5 w-5" />
    </Link>
    <div class="flex-1">
      {#if loading}
        <h1 class="text-lg font-semibold">Loading...</h1>
      {:else if polling.thread}
        <h1 class="text-lg font-semibold">
          {polling.thread.title || "New conversation"}
        </h1>
        <p class="text-sm text-muted-foreground">
          {#if polling.thread.status === "running" || polling.thread.status === "pending"}
            <Shimmer as="span" content_length={12}>Processing...</Shimmer>
          {:else if polling.thread.status === "error"}
            <span class="text-red-500">Error</span>
          {:else}
            Completed
          {/if}
        </p>
        <p class="text-xs text-muted-foreground">
          <span class="font-medium">DB:</span>
          {polling.thread.database_connection_name || selectedDatabaseLabel || "—"}
          <span class="mx-2">•</span>
          <span class="font-medium">Model:</span>
          {polling.thread.model_config_display_name || selectedModelLabel || "—"}
        </p>
      {:else}
        <h1 class="text-lg font-semibold">Thread not found</h1>
      {/if}
    </div>

    <Link
      href="/settings/"
      class="text-muted-foreground transition-colors hover:text-foreground"
      aria-label="Settings"
    >
      <Settings class="h-5 w-5" />
    </Link>
  </header>

  <div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-6">
    {#if loading}
      <div class="flex h-full items-center justify-center">
        <p class="text-muted-foreground">Loading messages...</p>
      </div>
    {:else if polling.messages.length === 0}
      <div class="flex h-full items-center justify-center">
        <div class="text-center">
          <p class="text-muted-foreground">No messages in this thread</p>
        </div>
      </div>
    {:else}
      <div class="mx-auto max-w-4xl space-y-6">
        {#each displayMessages as item (getDisplayItemKey(item))}
          {#if "call" in item}
            <ToolExecution
              toolName={item.call.content.tool_name || "unknown"}
              args={item.call.content.tool_args}
              result={item.result?.content.result}
            />
          {:else if item.type === "user"}
            <Message from="user">
              <MessageContent>{item.content.text}</MessageContent>
            </Message>
          {:else if item.type === "assistant"}
            <Message from="assistant">
              <MessageResponse content={item.content.text || ""} />
            </Message>
          {:else if item.type === "thinking"}
            <ThinkingBlock content={item.content.text || ""} />
          {/if}
        {/each}

        {#if polling.isPolling}
          <Message from="assistant">
            <div class="space-y-2">
              <Shimmer content_length={40}>Crunching data...</Shimmer>
            </div>
          </Message>
        {/if}
      </div>
    {/if}
  </div>

  <div class="p-4">
    <div class="mx-auto max-w-4xl">
      <PromptInput onSubmit={handleSubmit} class={controlsDisabled ? "opacity-50" : ""}>
        <PromptInputBody>
          <PromptInputTextarea
            placeholder="Ask a follow-up question..."
            disabled={controlsDisabled}
          />
        </PromptInputBody>
        <PromptInputToolbar>
          <div class="flex items-center gap-2">
            <PromptInputModelSelect bind:value={selectedDatabaseId} disabled={controlsDisabled}>
              <PromptInputModelSelectTrigger>
                <PromptInputModelSelectValue
                  placeholder="DB"
                  value={selectedDatabaseLabel}
                />
              </PromptInputModelSelectTrigger>
              <PromptInputModelSelectContent>
                {#each activeDatabaseConnections as db (db.id)}
                  <PromptInputModelSelectItem value={String(db.id)}>
                    {db.name}
                  </PromptInputModelSelectItem>
                {/each}
              </PromptInputModelSelectContent>
            </PromptInputModelSelect>

            <PromptInputModelSelect bind:value={selectedModelId} disabled={controlsDisabled}>
              <PromptInputModelSelectTrigger>
                <PromptInputModelSelectValue
                  placeholder="Model"
                  value={selectedModelLabel}
                />
              </PromptInputModelSelectTrigger>
              <PromptInputModelSelectContent>
                {#each activeModelConfigs as m (m.id)}
                  <PromptInputModelSelectItem value={String(m.id)}>
                    {m.display_name}
                  </PromptInputModelSelectItem>
                {/each}
              </PromptInputModelSelectContent>
            </PromptInputModelSelect>
          </div>

          <PromptInputSubmit
            status={polling.chatStatus}
            disabled={sendDisabled}
          />
        </PromptInputToolbar>
      </PromptInput>
    </div>
  </div>
</div>
