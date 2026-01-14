<script lang="ts">
	import { PromptInputController, setPromptInputProvider } from "./attachments-context.svelte.js";

	interface Props {
		initialInput?: string;
		accept?: string;
		multiple?: boolean;
		children?: import("svelte").Snippet;
	}

	let { initialInput = "", accept, multiple = true, children }: Props = $props();

	let controller = new PromptInputController();
	let didInit = false;

	$effect.pre(() => {
		if (!didInit) {
			controller.textInput.value = initialInput;
			didInit = true;
		}
	});

	$effect.pre(() => {
		controller.attachments.setOptions({ accept, multiple });
	});

	setPromptInputProvider(controller);
</script>

{#if children}
	{@render children()}
{/if}
