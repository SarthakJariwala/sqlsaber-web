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
 * ## Usage
 * ```svelte
 * <script lang="ts">
 *   import { UseThreadPolling } from "$lib/hooks/use-thread-polling.svelte";
 *
 *   const polling = new UseThreadPolling();
 *
 *   // Start polling for a thread
 *   polling.start(threadId);
 *
 * </script>
 * ```
 */
export class UseThreadPolling {
  #messages = $state<MessageData[]>([]);
  #thread = $state<ThreadData | null>(null);
  #chatStatus = $state<ChatStatus>("idle");
  #lastServerMessageId = $state<number>(0);
  #pollInterval: ReturnType<typeof setInterval> | null = null;
  #interval: number;

  constructor({ interval = 1000 }: ThreadPollingOptions = {}) {
    this.#interval = interval;
  }

  /** Current messages in the thread */
  get messages() {
    return this.#messages;
  }

  /** Set messages directly (for optimistic updates) */
  set messages(value: MessageData[]) {
    this.#messages = value;
  }

  /** Current thread data */
  get thread() {
    return this.#thread;
  }

  /** Set thread directly */
  set thread(value: ThreadData | null) {
    this.#thread = value;
  }

  /** Current chat status */
  get chatStatus() {
    return this.#chatStatus;
  }

  /** Set chat status directly */
  set chatStatus(value: ChatStatus) {
    this.#chatStatus = value;
  }

  /** Whether polling is currently active based on thread status */
  get isPolling() {
    return (
      this.#thread !== null &&
      (this.#thread.status === "pending" || this.#thread.status === "running")
    );
  }

  /** Whether a new message can be submitted */
  get canSubmit() {
    return (
      this.#chatStatus === "idle" &&
      (!this.#thread ||
        this.#thread.status === "completed" ||
        this.#thread.status === "error")
    );
  }

  /** Start polling for a thread */
  start() {
    if (this.#pollInterval) return;

    this.#pollInterval = setInterval(async () => {
      if (!this.#thread) return;

      try {
        const response = await axios.get<MessagesApiResponse>(
          `/api/threads/${this.#thread.id}/messages/`,
          {
            params:
              this.#lastServerMessageId > 0
                ? { after: this.#lastServerMessageId }
                : {},
          }
        );

        this.#thread = response.data.thread;

        if (response.data.messages.length > 0) {
          const newMessages = response.data.messages;
          this.#lastServerMessageId = newMessages[newMessages.length - 1].id;

          // Replace temp user message if server returned the real one
          const lastMsg = this.#messages[this.#messages.length - 1];
          const hasTempMessage = lastMsg && isTempMessageId(lastMsg.id);
          const serverHasUserMessage = newMessages.some(
            (m) => m.type === "user"
          );

          if (hasTempMessage && serverHasUserMessage) {
            this.#messages = [...this.#messages.slice(0, -1), ...newMessages];
          } else {
            this.#messages = [...this.#messages, ...newMessages];
          }
        }

        // Stop polling if thread is done
        if (
          this.#thread.status === "completed" ||
          this.#thread.status === "error"
        ) {
          this.stop();
          this.#chatStatus = "idle";
        }
      } catch (error) {
        console.error("Polling error:", error);
        this.stop();
        this.#chatStatus = "error";
        if (this.#thread) {
          this.#thread = { ...this.#thread, status: "error" };
        }
      }
    }, this.#interval);
  }

  /** Stop polling */
  stop() {
    if (this.#pollInterval) {
      clearInterval(this.#pollInterval);
      this.#pollInterval = null;
    }
  }

  /** Load initial thread data */
  async loadThread(threadId: number): Promise<void> {
    try {
      const response = await axios.get<MessagesApiResponse>(
        `/api/threads/${threadId}/messages/`
      );
      this.#thread = response.data.thread;
      this.#messages = response.data.messages;

      if (this.#messages.length > 0) {
        this.#lastServerMessageId =
          this.#messages[this.#messages.length - 1].id;
      }

      // Start polling if thread is still running
      if (
        this.#thread.status === "pending" ||
        this.#thread.status === "running"
      ) {
        this.start();
      }
    } catch (error) {
      console.error("Failed to load thread:", error);
      throw error;
    }
  }

  /** Add a temporary user message for optimistic UI updates */
  addTempUserMessage(text: string) {
    this.#messages = [
      ...this.#messages,
      {
        id: Date.now(),
        type: "user",
        content: { text },
        created_at: new Date().toISOString(),
      },
    ];
  }

  /** Update thread status to running (for optimistic updates) */
  setRunning() {
    if (this.#thread) {
      this.#thread = { ...this.#thread, status: "running" };
    }
  }

  /** Reset all state */
  reset() {
    this.stop();
    this.#messages = [];
    this.#thread = null;
    this.#chatStatus = "idle";
    this.#lastServerMessageId = 0;
  }
}
