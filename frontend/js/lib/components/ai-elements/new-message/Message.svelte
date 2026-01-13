<script lang="ts">
	import { cn } from "$lib/utils";
	import type { Snippet } from "svelte";
	import type { HTMLAttributes } from "svelte/elements";
	import type { MessageRole } from "./message-context.svelte.js";

	interface Props extends HTMLAttributes<HTMLDivElement> {
		from: MessageRole;
		class?: string;
		children: Snippet;
	}

	let { from, class: className, children, ...restProps }: Props = $props();
</script>

<div
	class={cn(
		"group flex w-full flex-col gap-2",
		from === "user"
			? "is-user ml-auto justify-end max-w-[80%]"
			: "is-assistant max-w-[95%]",
		className
	)}
	data-role={from}
	{...restProps}
>
	{@render children()}
</div>
