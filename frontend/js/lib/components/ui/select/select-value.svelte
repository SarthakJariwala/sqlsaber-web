<script lang="ts">
	import { cn } from "$lib/utils";

	interface Props {
		class?: string;
		placeholder?: string;
		value?: string;
		[key: string]: unknown;
	}

	let { class: className, placeholder, value, ...props }: Props = $props();
</script>

<span data-slot="select-value" class={cn(className)} {...props}>
	{#if value}
		{value}
	{:else if placeholder}
		{placeholder}
	{/if}
</span>
