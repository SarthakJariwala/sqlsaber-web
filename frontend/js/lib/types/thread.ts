// Thread and message types shared across pages

export type ThreadStatus = "pending" | "running" | "completed" | "error";

export interface MessageData {
  id: number;
  type: "user" | "assistant" | "thinking" | "tool_call" | "tool_result";
  content: {
    text?: string;
    tool_name?: string;
    tool_args?: unknown;
    result?: unknown;
  };
  created_at: string;
}

// Summary type for thread lists (without error details)
export interface ThreadSummary {
  id: number;
  title: string;
  status: ThreadStatus;
  database_connection_id: number | null;
  database_connection_name: string | null;
  database_connection_is_active: boolean | null;
  model_config_id: number | null;
  model_config_display_name: string | null;
  model_config_model_name: string | null;
  model_config_is_active: boolean | null;
  created_at: string;
  updated_at: string;
}

// Full thread data including error details
export interface ThreadData extends ThreadSummary {
  error: string | null;
}

export interface MessagesApiResponse {
  thread: ThreadData;
  messages: MessageData[];
}

// Type for display items - merges tool_call with its result
export type ToolDisplayItem = {
  type: "tool";
  call: MessageData;
  result?: MessageData;
};

export type DisplayItem = MessageData | ToolDisplayItem;

// Helper to get unique key for each display item
export function getDisplayItemKey(item: DisplayItem): number {
  if ("call" in item) {
    return item.call.id;
  }
  return item.id;
}

// Merge tool_call and tool_result messages into single items for display
export function mergeToolMessages(messages: MessageData[]): DisplayItem[] {
  const result: DisplayItem[] = [];

  for (const msg of messages) {
    if (msg.type === "tool_call") {
      result.push({ type: "tool", call: msg });
    } else if (msg.type === "tool_result") {
      // Find the matching tool call (most recent one with same name without result)
      const toolName = msg.content.tool_name || "unknown";
      for (let i = result.length - 1; i >= 0; i--) {
        const item = result[i];
        if (
          "call" in item &&
          item.call.content.tool_name === toolName &&
          !item.result
        ) {
          item.result = msg;
          break;
        }
      }
    } else {
      result.push(msg);
    }
  }

  return result;
}

// Check if a message ID is a temporary client-side ID (timestamp-based)
export function isTempMessageId(id: number): boolean {
  return id > 1000000000000;
}

// Format a date string for display
export function formatThreadDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Status badge style mappings
export const STATUS_BADGE_STYLES: Record<ThreadStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  running: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};
