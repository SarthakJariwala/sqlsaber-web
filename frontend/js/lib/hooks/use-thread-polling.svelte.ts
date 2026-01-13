import axios from "axios";
import type {
  MessageData,
  ThreadData,
  MessagesApiResponse,
} from "$lib/types/thread";
import { isTempMessageId } from "$lib/types/thread";

type ChatStatus = "idle" | "submitted" | "streaming" | "error";

type ThreadPollingOptions = {
  /** Polling interval in milliseconds. Defaults to 1000. */
  interval?: number;
};

/**
 * Hook for polling thread messages from the server.
 *
 * Uses Svelte 5's $effect for lifecycle management - polling starts/stops
 * automatically based on thread status and cleans up on component destroy.
 *
 * ## Usage
 * ```svelte
 * <script lang="ts">
 *   import { useThreadPolling } from "$lib/hooks/use-thread-polling.svelte";
 *
 *   const polling = useThreadPolling(props.thread, props.messages);
 * </script>
 * ```
 */
export function useThreadPolling(
  initialThread: ThreadData | null,
  initialMessages: MessageData[],
  { interval = 1000 }: ThreadPollingOptions = {}
) {
  let thread = $state<ThreadData | null>(initialThread);
  let messages = $state<MessageData[]>(initialMessages);
  let chatStatus = $state<ChatStatus>("idle");
  let lastServerMessageId = $state<number>(
    initialMessages.length ? initialMessages[initialMessages.length - 1].id : 0
  );

  const isPolling = $derived(
    thread !== null &&
      (thread.status === "pending" || thread.status === "running")
  );

  const canSubmit = $derived(
    chatStatus === "idle" &&
      (!thread || thread.status === "completed" || thread.status === "error")
  );

  async function pollOnce() {
    if (!thread) return;

    const response = await axios.get<MessagesApiResponse>(
      `/api/threads/${thread.id}/messages/`,
      {
        params:
          lastServerMessageId > 0 ? { after: lastServerMessageId } : {},
      }
    );

    thread = response.data.thread;

    if (response.data.messages.length > 0) {
      const newMessages = response.data.messages;
      lastServerMessageId = newMessages[newMessages.length - 1].id;

      const lastMsg = messages[messages.length - 1];
      const hasTempMessage = lastMsg && isTempMessageId(lastMsg.id);
      const serverHasUserMessage = newMessages.some((m) => m.type === "user");

      if (hasTempMessage && serverHasUserMessage) {
        messages = [...messages.slice(0, -1), ...newMessages];
      } else {
        messages = [...messages, ...newMessages];
      }
    }

    if (thread.status === "completed" || thread.status === "error") {
      chatStatus = "idle";
    }
  }

  $effect(() => {
    if (!thread) return;
    if (thread.status !== "pending" && thread.status !== "running") return;

    const handle = setInterval(async () => {
      try {
        await pollOnce();
      } catch (error) {
        console.error("Polling error:", error);
        chatStatus = "error";
        if (thread) {
          thread = { ...thread, status: "error" };
        }
      }
    }, interval);

    return () => clearInterval(handle);
  });

  function addTempUserMessage(text: string) {
    messages = [
      ...messages,
      {
        id: Date.now(),
        type: "user",
        content: { text },
        created_at: new Date().toISOString(),
      },
    ];
  }

  function setRunning() {
    if (thread) {
      thread = { ...thread, status: "running" };
    }
  }

  function setChatStatus(status: ChatStatus) {
    chatStatus = status;
  }

  function reset() {
    messages = [];
    thread = null;
    chatStatus = "idle";
    lastServerMessageId = 0;
  }

  return {
    get thread() {
      return thread;
    },
    get messages() {
      return messages;
    },
    get chatStatus() {
      return chatStatus;
    },
    get isPolling() {
      return isPolling;
    },
    get canSubmit() {
      return canSubmit;
    },
    addTempUserMessage,
    setRunning,
    setChatStatus,
    reset,
  };
}
