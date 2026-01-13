<script lang="ts">
  import { Link, router } from "@inertiajs/svelte";
  import axios from "axios";
  import { Menu, Settings } from "@lucide/svelte";
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
    type DatabaseConnection,
    type ModelConfig,
  } from "$lib/types/thread";
  import { useThreadPolling } from "$lib/hooks/use-thread-polling.svelte";

  interface Props {
    configured: boolean;
    onboarding_completed: boolean;
    defaults: {
      database_connection_id: number | null;
      model_config_id: number | null;
    };
    database_connections: DatabaseConnection[];
    model_configs: ModelConfig[];
  }

  let props = $props<Props>();

  if (!props.configured) {
    router.visit("/settings/");
  }

  const polling = useThreadPolling(null, []);
  let messagesContainer: HTMLDivElement | null = null;

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
    props.defaults.database_connection_id
      ? String(props.defaults.database_connection_id)
      : ""
  );
  let selectedModelId = $state(
    props.defaults.model_config_id
      ? String(props.defaults.model_config_id)
      : ""
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
    if (!prompt) return;
    if (!selectedDatabaseId || !selectedModelId) {
      router.visit("/settings/");
      return;
    }

    polling.setChatStatus("submitted");

    try {
      if (!polling.thread) {
        const response = await axios.post<{ id: number }>("/api/threads/", {
          prompt,
          database_connection_id: Number(selectedDatabaseId),
          model_config_id: Number(selectedModelId),
        });

        router.visit(`/threads/${response.data.id}/`);
        return;
      } else {
        await axios.post(`/api/threads/${polling.thread.id}/continue/`, {
          prompt,
          database_connection_id: Number(selectedDatabaseId),
          model_config_id: Number(selectedModelId),
        });
        polling.setRunning();
        polling.addTempUserMessage(prompt);
      }
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
      <Menu class="h-5 w-5" />
    </Link>
    <h1 class="text-lg font-semibold">sqlsaber</h1>
    {#if polling.thread}
      <p class="flex-1 text-sm text-muted-foreground">
        {polling.thread.title || "New conversation"}
        {#if polling.thread.status === "running" || polling.thread.status === "pending"}
          <Shimmer as="span" content_length={12} class="ml-2"
            >Processing...</Shimmer
          >
        {:else if polling.thread.status === "error"}
          <span class="ml-2 text-red-500">Error</span>
        {/if}
      </p>
    {:else}
      <p class="flex-1 text-sm text-muted-foreground">
        <span class="font-medium">DB:</span>
        {selectedDatabaseLabel || "—"}
        <span class="mx-2">•</span>
        <span class="font-medium">Model:</span>
        {selectedModelLabel || "—"}
      </p>
    {/if}
    <Link
      href="/settings/"
      class="ml-auto text-muted-foreground transition-colors hover:text-foreground"
      aria-label="Settings"
    >
      <Settings class="h-5 w-5" />
    </Link>
  </header>

  <div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-6">
    {#if polling.messages.length === 0}
      <div class="flex h-full items-center justify-center">
        <div class="text-center">
          <h2 class="text-xl font-semibold text-muted-foreground">
            Welcome to sqlsaber
          </h2>
          <p class="mt-2 text-sm text-muted-foreground">
            You can ask questions about your data in plain english.
          </p>
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
      <PromptInput
        onSubmit={handleSubmit}
        class={controlsDisabled ? "opacity-50" : ""}
      >
        <PromptInputBody>
          <PromptInputTextarea
            placeholder={polling.thread
              ? "Ask a follow-up question..."
              : "What would you like to know about your data?"}
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

          <PromptInputSubmit status={polling.chatStatus} disabled={sendDisabled} />
        </PromptInputToolbar>
      </PromptInput>
    </div>
  </div>
</div>
