<script lang="ts">
  import { Link, router, page } from "@inertiajs/svelte";
  import { ChevronLeft } from "@lucide/svelte";

  import { Button } from "$lib/components/ui/button";
  import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
  } from "$lib/components/ui/card";
  import {
    Field,
    FieldContent,
    FieldDescription,
    FieldLabel,
  } from "$lib/components/ui/field";
  import { Input } from "$lib/components/ui/input";
  import { Separator } from "$lib/components/ui/separator";
  import { Textarea } from "$lib/components/ui/textarea";
  import * as Select from "$lib/components/ui/select/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";

  type DatabaseConnection = {
    id: number;
    name: string;
    memory: string;
    is_active: boolean;
  };

  type ApiKey = {
    id: number;
    provider: string;
    name: string;
    preview: string;
    is_active: boolean;
  };

  type ModelConfig = {
    id: number;
    display_name: string;
    provider: string;
    model_name: string;
    api_key_id: number;
    api_key_is_active: boolean;
    is_active: boolean;
  };

  type AvailableModel = {
    id: string;
    name: string;
    description: string | null;
    context_length: number | null;
  };

  type AvailableModelsCatalog = {
    providers: { key: string; label: string }[];
    models_by_provider: Record<string, AvailableModel[]>;
  };

  interface Props {
    configured: boolean;
    onboarding_completed: boolean;
    defaults: {
      database_connection_id: number | null;
      model_config_id: number | null;
    };
    database_connections: DatabaseConnection[];
    api_keys: ApiKey[];
    model_configs: ModelConfig[];
    available_models: AvailableModelsCatalog;
    errors?: Record<string, string>;
  }

  let props: Props = $props();

  let settingsTab = $state("database");

  let activeDatabaseConnections = $derived(
    props.database_connections.filter((d) => d.is_active)
  );
  let activeApiKeys = $derived(props.api_keys.filter((k) => k.is_active));
  let activeModelConfigs = $derived(
    props.model_configs.filter((m) => m.is_active && m.api_key_is_active)
  );

  let defaultDatabaseConnectionId = $state(
    props.defaults.database_connection_id
      ? String(props.defaults.database_connection_id)
      : ""
  );
  let defaultModelConfigId = $state(
    props.defaults.model_config_id ? String(props.defaults.model_config_id) : ""
  );

  const PROVIDER_LABELS: Record<string, string> = {
    openai: "OpenAI",
    anthropic: "Anthropic",
    google: "Google",
  };

  function providerLabel(provider: string) {
    return PROVIDER_LABELS[provider] ?? provider;
  }

  function apiKeyLabel(key: ApiKey) {
    const p = providerLabel(key.provider);
    return key.name ? `${p} — ${key.name}` : p;
  }

  function providerFromModelId(modelId: string) {
    if (!modelId || !modelId.includes(":")) return "";
    return modelId.split(":", 1)[0];
  }

  function modelLabelFromCatalog(modelId: string, providerHint: string) {
    if (!modelId) return "";
    const provider = providerHint || providerFromModelId(modelId);
    const models = props.available_models.models_by_provider[provider] ?? [];
    return models.find((m) => m.id === modelId)?.name ?? modelId;
  }

  let defaultDatabaseConnectionLabel = $derived(
    activeDatabaseConnections.find(
      (d) => String(d.id) === defaultDatabaseConnectionId
    )?.name ?? ""
  );
  let defaultModelConfigLabel = $derived(
    activeModelConfigs.find((m) => String(m.id) === defaultModelConfigId)
      ?.display_name ?? ""
  );

  let saveSuccess = $state<string | null>(null);

  // Add DB form
  let newDbName = $state("");
  let newDbConnectionString = $state("");
  let newDbMemory = $state("");
  let addingDb = $state(false);

  // Add key form
  let newKeyProvider = $state("openai");
  let newKeyName = $state("");
  let newKeyValue = $state("");
  let addingKey = $state(false);

  // Add model form
  let newModelDisplayName = $state("");
  let newModelName = $state("");
  let newModelApiKeyId = $state("");
  let addingModel = $state(false);

  // Edit state
  let editingDbId = $state<number | null>(null);
  let editDbName = $state("");
  let editDbConnectionString = $state("");
  let editDbMemory = $state("");
  let savingDbEdit = $state(false);

  let editingKeyId = $state<number | null>(null);
  let editKeyName = $state("");
  let editKeyValue = $state("");
  let savingKeyEdit = $state(false);

  let editingModelId = $state<number | null>(null);
  let editModelDisplayName = $state("");
  let editModelName = $state("");
  let editModelApiKeyId = $state("");
  let savingModelEdit = $state(false);

  let newModelApiKeyProvider = $derived(
    activeApiKeys.find((k) => String(k.id) === newModelApiKeyId)?.provider ?? ""
  );
  let newModelOptions = $derived(
    props.available_models.models_by_provider[newModelApiKeyProvider] ?? []
  );
  let newModelLabel = $derived(
    modelLabelFromCatalog(newModelName, newModelApiKeyProvider)
  );

  function apiKeyLabelForId(id: string) {
    const key = activeApiKeys.find((k) => String(k.id) === id);
    return key ? apiKeyLabel(key) : "";
  }

  let newModelApiKeyLabel = $derived(apiKeyLabelForId(newModelApiKeyId));
  let editModelApiKeyLabel = $derived(apiKeyLabelForId(editModelApiKeyId));

  let editModelApiKeyProvider = $derived(
    activeApiKeys.find((k) => String(k.id) === editModelApiKeyId)?.provider ??
      providerFromModelId(editModelName)
  );
  let editModelOptions = $derived(
    props.available_models.models_by_provider[editModelApiKeyProvider] ?? []
  );
  let editModelLabel = $derived(
    modelLabelFromCatalog(editModelName, editModelApiKeyProvider)
  );

  $effect(() => {
    if (activeApiKeys.length > 0) {
      const providerIsSupported = Boolean(
        props.available_models.models_by_provider[newModelApiKeyProvider]
      );
      if (!providerIsSupported) {
        const supportedKey = activeApiKeys.find((k) =>
          Boolean(props.available_models.models_by_provider[k.provider])
        );
        if (supportedKey && String(supportedKey.id) !== newModelApiKeyId) {
          newModelApiKeyId = String(supportedKey.id);
        }
      }
    }

    if (
      newModelName &&
      newModelApiKeyProvider &&
      !newModelName.startsWith(`${newModelApiKeyProvider}:`)
    ) {
      newModelName = "";
    }

    if (!newModelDisplayName && newModelName) {
      const label = modelLabelFromCatalog(newModelName, newModelApiKeyProvider);
      if (label) {
        newModelDisplayName = label;
      }
    }

    if (
      editModelName &&
      editModelApiKeyProvider &&
      !editModelName.startsWith(`${editModelApiKeyProvider}:`)
    ) {
      editModelName = "";
    }
  });

  let savingConfig = $state(false);

  let canFinish = $derived(
    defaultDatabaseConnectionId !== "" && defaultModelConfigId !== ""
  );

  function resetBanner() {
    saveSuccess = null;
  }

  function postInertia(
    url: string,
    data: Record<string, unknown>,
    options: {
      onSuccess?: () => void;
      onFinish?: () => void;
      successMessage?: string;
    } = {}
  ) {
    resetBanner();
    router.post(url, data, {
      preserveScroll: true,
      onSuccess: () => {
        if (options.successMessage) {
          saveSuccess = options.successMessage;
        }
        options.onSuccess?.();
      },
      onFinish: () => {
        options.onFinish?.();
      },
    });
  }

  // --------------------------------------------------------------------------
  // Add handlers
  // --------------------------------------------------------------------------
  function addDatabaseConnection() {
    addingDb = true;
    postInertia(
      "/settings/db-connections/add/",
      {
        name: newDbName,
        connection_string: newDbConnectionString,
        memory: newDbMemory,
      },
      {
        successMessage: "Database connection added.",
        onSuccess: () => {
          newDbName = "";
          newDbConnectionString = "";
          newDbMemory = "";
        },
        onFinish: () => {
          addingDb = false;
        },
      }
    );
  }

  function addApiKey() {
    addingKey = true;
    postInertia(
      "/settings/api-keys/add/",
      {
        provider: newKeyProvider,
        name: newKeyName,
        api_key: newKeyValue,
      },
      {
        successMessage: "API key added.",
        onSuccess: () => {
          newKeyName = "";
          newKeyValue = "";
        },
        onFinish: () => {
          addingKey = false;
        },
      }
    );
  }

  function addModelConfig() {
    if (newModelApiKeyId === "") {
      return;
    }
    addingModel = true;
    postInertia(
      "/settings/models/add/",
      {
        display_name: newModelDisplayName,
        model_name: newModelName,
        api_key_id: Number(newModelApiKeyId),
      },
      {
        successMessage: "Model added.",
        onSuccess: () => {
          newModelDisplayName = "";
          newModelName = "";
        },
        onFinish: () => {
          addingModel = false;
        },
      }
    );
  }

  // --------------------------------------------------------------------------
  // Update / Active toggles
  // --------------------------------------------------------------------------
  function startEditDb(db: DatabaseConnection) {
    editingDbId = db.id;
    editDbName = db.name;
    editDbConnectionString = "";
    editDbMemory = db.memory ?? "";
  }

  function saveDbEdit() {
    if (editingDbId === null) return;
    savingDbEdit = true;

    const payload: Record<string, unknown> = {
      name: editDbName,
      memory: editDbMemory,
    };
    if (editDbConnectionString.trim() !== "") {
      payload.connection_string = editDbConnectionString;
    }

    postInertia(`/settings/db-connections/${editingDbId}/update/`, payload, {
      successMessage: "Database connection updated.",
      onSuccess: () => {
        editingDbId = null;
      },
      onFinish: () => {
        savingDbEdit = false;
      },
    });
  }

  function setDbActive(id: number, is_active: boolean) {
    postInertia(
      `/settings/db-connections/${id}/set-active/`,
      { is_active },
      {
        successMessage: is_active ? "Database restored." : "Database removed.",
      }
    );
  }

  function startEditKey(key: ApiKey) {
    editingKeyId = key.id;
    editKeyName = key.name;
    editKeyValue = "";
  }

  function saveKeyEdit() {
    if (editingKeyId === null) return;
    savingKeyEdit = true;

    const payload: Record<string, unknown> = { name: editKeyName };
    if (editKeyValue.trim() !== "") {
      payload.api_key = editKeyValue;
    }

    postInertia(`/settings/api-keys/${editingKeyId}/update/`, payload, {
      successMessage: "API key updated.",
      onSuccess: () => {
        editingKeyId = null;
      },
      onFinish: () => {
        savingKeyEdit = false;
      },
    });
  }

  function setKeyActive(id: number, is_active: boolean) {
    postInertia(
      `/settings/api-keys/${id}/set-active/`,
      { is_active },
      {
        successMessage: is_active ? "API key restored." : "API key removed.",
      }
    );
  }

  function startEditModel(model: ModelConfig) {
    editingModelId = model.id;
    editModelDisplayName = model.display_name;
    editModelName = model.model_name;
    editModelApiKeyId = String(model.api_key_id);
  }

  function saveModelEdit() {
    if (editingModelId === null) return;
    savingModelEdit = true;

    postInertia(
      `/settings/models/${editingModelId}/update/`,
      {
        display_name: editModelDisplayName,
        model_name: editModelName,
        api_key_id: Number(editModelApiKeyId),
      },
      {
        successMessage: "Model updated.",
        onSuccess: () => {
          editingModelId = null;
        },
        onFinish: () => {
          savingModelEdit = false;
        },
      }
    );
  }

  function setModelActive(id: number, is_active: boolean) {
    postInertia(
      `/settings/models/${id}/set-active/`,
      { is_active },
      {
        successMessage: is_active ? "Model restored." : "Model removed.",
      }
    );
  }

  // --------------------------------------------------------------------------
  // Save defaults (complete setup)
  // --------------------------------------------------------------------------
  function saveSettings({ complete }: { complete: boolean }) {
    savingConfig = true;
    resetBanner();

    router.post(
      "/settings/config/update/",
      {
        default_database_connection_id: defaultDatabaseConnectionId
          ? Number(defaultDatabaseConnectionId)
          : null,
        default_model_config_id: defaultModelConfigId
          ? Number(defaultModelConfigId)
          : null,
        onboarding_completed: complete,
      },
      {
        preserveScroll: true,
        onSuccess: () => {
          if (complete) {
            router.visit("/");
          } else {
            saveSuccess = "Saved.";
          }
        },
        onFinish: () => {
          savingConfig = false;
        },
      }
    );
  }

  // Get first error message from errors prop
  let errorMessage = $derived(
    props.errors ? Object.values(props.errors)[0] : null
  );
</script>

<div class="flex h-screen flex-col">
  <header class="flex items-center justify-between border-b px-4 py-3">
    <div class="flex items-center gap-3">
      {#if props.configured}
        <Link
          href="/threads/"
          class="text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft class="h-5 w-5" />
        </Link>
      {/if}
      <h1 class="text-lg font-semibold">
        {#if props.onboarding_completed}
          Settings
        {:else}
          Setup
        {/if}
      </h1>
    </div>
  </header>

  <main class="flex-1 overflow-y-auto">
    <div class="mx-auto w-full max-w-3xl space-y-10 p-6">
      {#if !props.configured}
        <div class="rounded-lg border bg-muted/30 p-4 text-sm">
          <p class="font-medium">Finish setup to start chatting.</p>
          <p class="mt-1 text-muted-foreground">
            Add at least one database connection and one model, choose defaults,
            and click <span class="font-medium">Complete setup</span>.
          </p>
        </div>
      {/if}

      <Tabs.Root bind:value={settingsTab}>
        <Tabs.List class="w-full">
          <Tabs.Trigger value="database">Database</Tabs.Trigger>
          <Tabs.Trigger value="api_keys">API keys</Tabs.Trigger>
          <Tabs.Trigger value="models">Models</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="database" class="pt-4">
          <!-- 1) Database connections -->
          <section class="space-y-4">
            <h2 class="text-base font-semibold">Database connections</h2>

            <Field>
              <FieldLabel>Default database</FieldLabel>
              <FieldContent>
                <Select.Root
                  type="single"
                  bind:value={defaultDatabaseConnectionId}
                >
                  <Select.Trigger
                    class="w-full"
                    data-placeholder={defaultDatabaseConnectionId === ""
                      ? ""
                      : undefined}
                  >
                    <Select.Value
                      value={defaultDatabaseConnectionLabel}
                      placeholder="Select a database connection"
                    />
                  </Select.Trigger>
                  <Select.Content class="w-full">
                    {#each activeDatabaseConnections as db (db.id)}
                      <Select.Item value={String(db.id)} label={db.name} />
                    {/each}
                  </Select.Content>
                </Select.Root>
                <FieldDescription>
                  Used for new threads unless you pick another DB in the prompt
                  input.
                </FieldDescription>
              </FieldContent>
            </Field>

            <div class="space-y-3">
              {#if props.database_connections.length === 0}
                <p class="text-sm text-muted-foreground">
                  No database connections yet.
                </p>
              {:else}
                {#each props.database_connections as db (db.id)}
                  <Card class="py-3">
                    <CardContent class="space-y-3">
                      <div class="flex items-start justify-between gap-3">
                        <div class="min-w-0 flex-1">
                          <div class="flex items-center gap-2">
                            <span class="truncate font-medium">{db.name}</span>
                            {#if !db.is_active}
                              <span
                                class="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                              >
                                removed
                              </span>
                            {/if}
                            {#if db.is_active && (db.memory || "").trim() !== ""}
                              <span
                                class="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                              >
                                memory set
                              </span>
                            {/if}
                          </div>
                        </div>
                        <div class="flex items-center gap-2">
                          {#if db.is_active}
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => startEditDb(db)}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              type="button"
                              onclick={() => setDbActive(db.id, false)}
                            >
                              Remove
                            </Button>
                          {:else}
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => setDbActive(db.id, true)}
                            >
                              Restore
                            </Button>
                          {/if}
                        </div>
                      </div>

                      {#if editingDbId === db.id}
                        <Separator />
                        <div class="grid gap-3">
                          <div class="grid gap-3 md:grid-cols-2">
                            <Field>
                              <FieldLabel>Name</FieldLabel>
                              <FieldContent>
                                <Input
                                  bind:value={editDbName}
                                  autocomplete="off"
                                />
                              </FieldContent>
                            </Field>
                            <Field>
                              <FieldLabel>New connection string</FieldLabel>
                              <FieldContent>
                                <Input
                                  bind:value={editDbConnectionString}
                                  placeholder="Leave blank to keep existing"
                                  autocomplete="off"
                                />
                              </FieldContent>
                            </Field>
                          </div>

                          <Field>
                            <FieldLabel>DB-specific memory</FieldLabel>
                            <FieldContent>
                              <Textarea
                                rows={5}
                                bind:value={editDbMemory}
                                placeholder="Injected only when running against this DB"
                              />
                            </FieldContent>
                          </Field>

                          <div class="flex items-center gap-2">
                            <Button
                              size="sm"
                              type="button"
                              disabled={savingDbEdit}
                              onclick={saveDbEdit}
                            >
                              {savingDbEdit ? "Saving..." : "Save"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => {
                                editingDbId = null;
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      {/if}
                    </CardContent>
                  </Card>
                {/each}
              {/if}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Add database connection</CardTitle>
              </CardHeader>
              <CardContent class="space-y-4">
                <div class="grid gap-4 md:grid-cols-2">
                  <Field>
                    <FieldLabel for="db-name">Name</FieldLabel>
                    <FieldContent>
                      <Input
                        id="db-name"
                        placeholder="e.g. Analytics prod"
                        bind:value={newDbName}
                        autocomplete="off"
                      />
                    </FieldContent>
                  </Field>

                  <Field>
                    <FieldLabel for="db-conn">Connection string</FieldLabel>
                    <FieldContent>
                      <Input
                        id="db-conn"
                        placeholder="e.g. postgresql://user:pass@host:5432/db"
                        bind:value={newDbConnectionString}
                        autocomplete="off"
                      />
                      <FieldDescription>
                        Stored in the database for your user.
                      </FieldDescription>
                    </FieldContent>
                  </Field>
                </div>

                <Field>
                  <FieldLabel for="db-memory"
                    >DB-specific memory (optional)</FieldLabel
                  >
                  <FieldContent>
                    <Textarea
                      id="db-memory"
                      rows={5}
                      placeholder="Injected only when running against this DB"
                      bind:value={newDbMemory}
                    />
                  </FieldContent>
                </Field>

                <div>
                  <Button
                    type="button"
                    disabled={addingDb}
                    onclick={addDatabaseConnection}
                  >
                    {addingDb ? "Adding..." : "Add database"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>
        </Tabs.Content>

        <Tabs.Content value="api_keys" class="pt-4">
          <!-- 2) API keys -->
          <section class="space-y-4">
            <h2 class="text-base font-semibold">API keys</h2>

            <div class="space-y-3">
              {#if props.api_keys.length === 0}
                <p class="text-sm text-muted-foreground">No API keys yet.</p>
              {:else}
                {#each props.api_keys as key (key.id)}
                  <Card class="py-3">
                    <CardContent class="space-y-3">
                      <div class="flex items-start justify-between gap-3">
                        <div class="min-w-0 flex-1">
                          <div class="flex items-center gap-2">
                            <span class="truncate">
                              <span class="font-medium">{key.provider}</span>
                              {#if key.name}
                                <span class="text-muted-foreground">
                                  — {key.name}</span
                                >
                              {/if}
                            </span>
                            {#if !key.is_active}
                              <span
                                class="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                              >
                                removed
                              </span>
                            {/if}
                          </div>
                          <p class="mt-1 text-xs text-muted-foreground">
                            {key.preview}
                          </p>
                        </div>
                        <div class="flex items-center gap-2">
                          {#if key.is_active}
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => startEditKey(key)}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              type="button"
                              onclick={() => setKeyActive(key.id, false)}
                            >
                              Remove
                            </Button>
                          {:else}
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => setKeyActive(key.id, true)}
                            >
                              Restore
                            </Button>
                          {/if}
                        </div>
                      </div>

                      {#if editingKeyId === key.id}
                        <Separator />
                        <div class="grid gap-3 md:grid-cols-2">
                          <Field>
                            <FieldLabel>Label (optional)</FieldLabel>
                            <FieldContent>
                              <Input
                                bind:value={editKeyName}
                                autocomplete="off"
                              />
                            </FieldContent>
                          </Field>

                          <Field>
                            <FieldLabel>New API key</FieldLabel>
                            <FieldContent>
                              <Input
                                type="password"
                                bind:value={editKeyValue}
                                placeholder="Leave blank to keep existing"
                                autocomplete="off"
                              />
                            </FieldContent>
                          </Field>

                          <div class="md:col-span-2 flex items-center gap-2">
                            <Button
                              size="sm"
                              type="button"
                              disabled={savingKeyEdit}
                              onclick={saveKeyEdit}
                            >
                              {savingKeyEdit ? "Saving..." : "Save"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => {
                                editingKeyId = null;
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      {/if}
                    </CardContent>
                  </Card>
                {/each}
              {/if}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Add API key</CardTitle>
              </CardHeader>
              <CardContent class="space-y-4">
                <div class="grid gap-4 md:grid-cols-2">
                  <Field>
                    <FieldLabel>Provider</FieldLabel>
                    <FieldContent>
                      <Select.Root type="single" bind:value={newKeyProvider}>
                        <Select.Trigger class="w-full">
                          <Select.Value value={providerLabel(newKeyProvider)} />
                        </Select.Trigger>
                        <Select.Content class="w-full">
                          <Select.Item value="openai" label="OpenAI" />
                          <Select.Item value="anthropic" label="Anthropic" />
                          <Select.Item value="google" label="Google" />
                        </Select.Content>
                      </Select.Root>
                    </FieldContent>
                  </Field>

                  <Field>
                    <FieldLabel for="key-name">Label (optional)</FieldLabel>
                    <FieldContent>
                      <Input
                        id="key-name"
                        placeholder="e.g. Production key"
                        bind:value={newKeyName}
                        autocomplete="off"
                      />
                    </FieldContent>
                  </Field>
                </div>

                <Field>
                  <FieldLabel for="api-key">API key</FieldLabel>
                  <FieldContent>
                    <Input
                      id="api-key"
                      type="password"
                      placeholder="Enter an API key"
                      bind:value={newKeyValue}
                      autocomplete="off"
                    />
                  </FieldContent>
                </Field>

                <div>
                  <Button
                    type="button"
                    disabled={addingKey}
                    onclick={addApiKey}
                  >
                    {addingKey ? "Adding..." : "Add API key"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>
        </Tabs.Content>

        <Tabs.Content value="models" class="pt-4">
          <!-- 3) Models -->
          <section class="space-y-4">
            <h2 class="text-base font-semibold">Models</h2>

            <Field>
              <FieldLabel>Default model</FieldLabel>
              <FieldContent>
                <Select.Root type="single" bind:value={defaultModelConfigId}>
                  <Select.Trigger
                    class="w-full"
                    data-placeholder={defaultModelConfigId === ""
                      ? ""
                      : undefined}
                  >
                    <Select.Value
                      value={defaultModelConfigLabel}
                      placeholder="Select a model"
                    />
                  </Select.Trigger>
                  <Select.Content class="w-full">
                    {#each activeModelConfigs as m (m.id)}
                      <Select.Item
                        value={String(m.id)}
                        label={m.display_name}
                      />
                    {/each}
                  </Select.Content>
                </Select.Root>
                <FieldDescription>
                  Used for new threads unless you pick another model in the
                  prompt input.
                </FieldDescription>
              </FieldContent>
            </Field>

            <div class="space-y-3">
              {#if props.model_configs.length === 0}
                <p class="text-sm text-muted-foreground">No models yet.</p>
              {:else}
                {#each props.model_configs as m (m.id)}
                  <Card class="py-3">
                    <CardContent class="space-y-3">
                      <div class="flex items-start justify-between gap-3">
                        <div class="min-w-0 flex-1">
                          <div class="flex items-center gap-2">
                            <span class="truncate font-medium"
                              >{m.display_name}</span
                            >
                            {#if !m.is_active}
                              <span
                                class="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                              >
                                removed
                              </span>
                            {:else if !m.api_key_is_active}
                              <span
                                class="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                              >
                                key inactive
                              </span>
                            {/if}
                          </div>
                          <p class="mt-1 text-xs text-muted-foreground">
                            {m.model_name}
                          </p>
                        </div>
                        <div class="flex items-center gap-2">
                          {#if m.is_active}
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => startEditModel(m)}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              type="button"
                              onclick={() => setModelActive(m.id, false)}
                            >
                              Remove
                            </Button>
                          {:else}
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => setModelActive(m.id, true)}
                            >
                              Restore
                            </Button>
                          {/if}
                        </div>
                      </div>

                      {#if editingModelId === m.id}
                        <Separator />
                        <div class="grid gap-3 md:grid-cols-2">
                          <Field>
                            <FieldLabel>Display name</FieldLabel>
                            <FieldContent>
                              <Input
                                bind:value={editModelDisplayName}
                                autocomplete="off"
                              />
                            </FieldContent>
                          </Field>

                          <Field>
                            <FieldLabel>Model</FieldLabel>
                            <FieldContent>
                              <Select.Root
                                type="single"
                                bind:value={editModelName}
                              >
                                <Select.Trigger
                                  class="w-full"
                                  data-placeholder={editModelName === ""
                                    ? ""
                                    : undefined}
                                >
                                  <Select.Value
                                    value={editModelLabel}
                                    placeholder="Select a model"
                                  />
                                </Select.Trigger>
                                <Select.Content class="w-full">
                                  {#if editModelOptions.length === 0}
                                    <Select.Item
                                      value=""
                                      label="No models available"
                                      disabled
                                    />
                                  {:else}
                                    {#each editModelOptions as model (model.id)}
                                      <Select.Item
                                        value={model.id}
                                        label={model.name}
                                      />
                                    {/each}
                                  {/if}
                                </Select.Content>
                              </Select.Root>
                            </FieldContent>
                          </Field>

                          <Field class="md:col-span-2">
                            <FieldLabel>API key for this model</FieldLabel>
                            <FieldContent>
                              <Select.Root
                                type="single"
                                bind:value={editModelApiKeyId}
                              >
                                <Select.Trigger
                                  class="w-full"
                                  data-placeholder={editModelApiKeyId === ""
                                    ? ""
                                    : undefined}
                                >
                                  <Select.Value
                                    value={editModelApiKeyLabel}
                                    placeholder="Select an API key"
                                  />
                                </Select.Trigger>
                                <Select.Content class="w-full">
                                  {#each activeApiKeys as key (key.id)}
                                    <Select.Item
                                      value={String(key.id)}
                                      label={apiKeyLabel(key)}
                                    />
                                  {/each}
                                </Select.Content>
                              </Select.Root>
                            </FieldContent>
                          </Field>

                          <div class="md:col-span-2 flex items-center gap-2">
                            <Button
                              size="sm"
                              type="button"
                              disabled={savingModelEdit}
                              onclick={saveModelEdit}
                            >
                              {savingModelEdit ? "Saving..." : "Save"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onclick={() => {
                                editingModelId = null;
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      {/if}
                    </CardContent>
                  </Card>
                {/each}
              {/if}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Add model</CardTitle>
              </CardHeader>
              <CardContent class="space-y-4">
                <div class="grid gap-4 md:grid-cols-2">
                  <Field>
                    <FieldLabel for="model-display">Display name</FieldLabel>
                    <FieldContent>
                      <Input
                        id="model-display"
                        placeholder="e.g. GPT-4o mini"
                        bind:value={newModelDisplayName}
                        autocomplete="off"
                      />
                    </FieldContent>
                  </Field>

                  <Field>
                    <FieldLabel>Model</FieldLabel>
                    <FieldContent>
                      <Select.Root
                        type="single"
                        bind:value={newModelName}
                        disabled={newModelApiKeyId === ""}
                      >
                        <Select.Trigger
                          class="w-full"
                          data-placeholder={newModelName === ""
                            ? ""
                            : undefined}
                        >
                          <Select.Value
                            value={newModelLabel}
                            placeholder={newModelApiKeyId === ""
                              ? "Select an API key first"
                              : "Select a model"}
                          />
                        </Select.Trigger>
                        <Select.Content class="w-full">
                          {#if newModelOptions.length === 0}
                            <Select.Item
                              value=""
                              label="No models available"
                              disabled
                            />
                          {:else}
                            {#each newModelOptions as model (model.id)}
                              <Select.Item
                                value={model.id}
                                label={model.name}
                              />
                            {/each}
                          {/if}
                        </Select.Content>
                      </Select.Root>
                      <FieldDescription>
                        Models are filtered by the selected API key's provider.
                      </FieldDescription>
                    </FieldContent>
                  </Field>
                </div>

                <Field>
                  <FieldLabel>API key for this model</FieldLabel>
                  <FieldContent>
                    <Select.Root type="single" bind:value={newModelApiKeyId}>
                      <Select.Trigger
                        class="w-full"
                        data-placeholder={newModelApiKeyId === ""
                          ? ""
                          : undefined}
                      >
                        <Select.Value
                          value={newModelApiKeyLabel}
                          placeholder="Select an API key"
                        />
                      </Select.Trigger>
                      <Select.Content class="w-full">
                        {#each activeApiKeys as key (key.id)}
                          <Select.Item
                            value={String(key.id)}
                            label={apiKeyLabel(key)}
                          />
                        {/each}
                      </Select.Content>
                    </Select.Root>
                    <FieldDescription>
                      A model can only reference one API key.
                    </FieldDescription>
                  </FieldContent>
                </Field>

                <div>
                  <Button
                    type="button"
                    disabled={addingModel || activeApiKeys.length === 0}
                    onclick={addModelConfig}
                  >
                    {addingModel ? "Adding..." : "Add model"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>
        </Tabs.Content>
      </Tabs.Root>

      {#if errorMessage}
        <p class="text-sm text-red-500">{errorMessage}</p>
      {/if}
      {#if saveSuccess}
        <p class="text-sm text-green-600">{saveSuccess}</p>
      {/if}

      <div class="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          disabled={savingConfig}
          onclick={() => saveSettings({ complete: false })}
        >
          Save
        </Button>
        <Button
          type="button"
          disabled={!canFinish || savingConfig}
          onclick={() => saveSettings({ complete: true })}
        >
          Complete setup
        </Button>
      </div>
    </div>
  </main>
</div>
