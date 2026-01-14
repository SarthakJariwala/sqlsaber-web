<script lang="ts">
	import { cn } from "$lib/utils";
	import { MessageBranchClass, setMessageBranchContext } from "./message-context.svelte.js";
	import type { Snippet } from "svelte";
	import type { HTMLAttributes } from "svelte/elements";

	interface Props extends HTMLAttributes<HTMLDivElement> {
		defaultBranch?: number;
		onBranchChange?: (branchIndex: number) => void;
		class?: string;
		children: Snippet;
	}

	let {
		defaultBranch = 0,
		onBranchChange,
		class: className,
		children,
		...restProps
	}: Props = $props();

	const branchContext = new MessageBranchClass();
	setMessageBranchContext(branchContext);

	let didInit = false;
	let previousBranch = $state(0);

	$effect.pre(() => {
		if (!didInit) {
			branchContext.currentBranch = defaultBranch;
			previousBranch = defaultBranch;
			didInit = true;
			return;
		}

		if (branchContext.currentBranch !== previousBranch) {
			previousBranch = branchContext.currentBranch;
			onBranchChange?.(branchContext.currentBranch);
		}
	});
</script>

<div class={cn("grid w-full gap-2 [&>div]:pb-0", className)} {...restProps}>
	{@render children()}
</div>
