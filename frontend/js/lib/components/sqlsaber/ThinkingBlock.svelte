<script lang="ts">
	import { cn } from "$lib/utils";
	import ChevronRightIcon from "@lucide/svelte/icons/chevron-right";
	import BrainIcon from "@lucide/svelte/icons/brain";
	import { slide } from "svelte/transition";

	interface Props {
		content: string;
		class?: string;
	}

	let { content, class: className }: Props = $props();

	let expanded = $state(false);

	function toggle() {
		expanded = !expanded;
	}
</script>

<div class={cn("my-2", className)}>
	<button
		type="button"
		onclick={toggle}
		class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
	>
		<ChevronRightIcon
			class={cn("size-4 transition-transform", expanded && "rotate-90")}
		/>
		<BrainIcon class="size-4" />
		<span>{expanded ? "Hide reasoning" : "View reasoning"}</span>
	</button>

	{#if expanded}
		<div
			transition:slide={{ duration: 200 }}
			class="mt-2 ml-6 pl-4 border-l-2 border-muted text-sm text-muted-foreground whitespace-pre-wrap"
		>
			{content}
		</div>
	{/if}
</div>
