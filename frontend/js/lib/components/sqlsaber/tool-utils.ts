// Tool display name mappings
export const TOOL_NAMES: Record<string, { pending: string; complete: string }> = {
	list_tables: {
		pending: "Listing database tables...",
		complete: "Listed database tables",
	},
	introspect_schema: {
		pending: "Inspecting table structure...",
		complete: "Inspected table structure",
	},
	execute_sql: {
		pending: "Running SQL query...",
		complete: "Executed SQL query",
	},
};

export function getToolDisplayName(
	toolName: string,
	status: "pending" | "complete"
): string {
	const names = TOOL_NAMES[toolName];
	if (names) {
		return names[status];
	}
	// Fallback: humanize the tool name
	const humanized = toolName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
	return status === "pending" ? `${humanized}...` : humanized;
}

// Type definitions for tool results
export interface TableInfo {
	table_schema: string;
	table_name: string;
	table_type: string;
	table_comment: string | null;
	full_name: string;
	name: string;
	schema: string;
	type: string;
}

export interface ListTablesResult {
	tables: TableInfo[];
	total_tables: number;
}

export interface ColumnInfo {
	type: string;
	nullable: boolean;
	default: string | null;
}

export interface SchemaInfo {
	columns: Record<string, ColumnInfo>;
	primary_keys: string[];
	foreign_keys: Array<{
		column: string;
		references_table: string;
		references_column: string;
	}>;
	indexes: string[];
}

export interface IntrospectSchemaResult {
	[tableName: string]: SchemaInfo;
}

export interface SqlResult {
	success: boolean;
	row_count: number;
	results: Record<string, unknown>[];
	truncated: boolean;
	error?: string;
}

function tryParseJson(value: unknown, fallback: unknown): unknown {
	if (typeof value !== "string") {
		return value;
	}
	try {
		return JSON.parse(value);
	} catch {
		return fallback;
	}
}

export function parseToolArgs(args: unknown): Record<string, unknown> {
	if (!args) {
		return {};
	}
	if (typeof args === "object" && args !== null) {
		return args as Record<string, unknown>;
	}
	if (typeof args === "string" && args.trim() === "") {
		return {};
	}
	const parsed = tryParseJson(args, { raw: args });
	return parsed as Record<string, unknown>;
}

export function parseToolResult(result: unknown): unknown {
	if (!result) {
		return null;
	}
	if (typeof result === "object") {
		return result;
	}
	return tryParseJson(result, result);
}

// Format SQL results as markdown table
export function formatSqlResultsAsMarkdown(result: SqlResult): string {
	if (!result.success) {
		return `**Error:** ${result.error || "Query failed"}`;
	}

	if (!result.results || result.results.length === 0) {
		return "*No results returned*";
	}

	const columns = Object.keys(result.results[0]);
	const header = `| ${columns.join(" | ")} |`;
	const separator = `| ${columns.map(() => "---").join(" | ")} |`;
	const rows = result.results.map(
		(row) => `| ${columns.map((col) => formatCellValue(row[col])).join(" | ")} |`
	);

	let markdown = [header, separator, ...rows].join("\n");

	if (result.truncated) {
		markdown += "\n\n*Results truncated*";
	}

	return markdown;
}

// Format schema as markdown
export function formatSchemaAsMarkdown(result: IntrospectSchemaResult): string {
	const parts: string[] = [];

	for (const [tableName, schema] of Object.entries(result)) {
		parts.push(`### ${tableName}\n`);

		// Columns table
		const columns = Object.entries(schema.columns);
		if (columns.length > 0) {
			parts.push("| Column | Type | Nullable | Default |");
			parts.push("| --- | --- | --- | --- |");
			for (const [colName, info] of columns) {
				parts.push(
					`| \`${colName}\` | ${info.type} | ${info.nullable ? "Yes" : "No"} | ${info.default ?? "-"} |`
				);
			}
			parts.push("");
		}

		// Primary keys
		if (schema.primary_keys && schema.primary_keys.length > 0) {
			parts.push(`**Primary Key:** ${schema.primary_keys.map((k) => `\`${k}\``).join(", ")}\n`);
		}

		// Foreign keys
		if (schema.foreign_keys && schema.foreign_keys.length > 0) {
			parts.push("**Foreign Keys:**");
			for (const fk of schema.foreign_keys) {
				parts.push(`- \`${fk.column}\` → \`${fk.references_table}.${fk.references_column}\``);
			}
			parts.push("");
		}

		// Indexes
		if (schema.indexes && schema.indexes.length > 0) {
			parts.push(`**Indexes:** ${schema.indexes.map((i) => `\`${i}\``).join(", ")}\n`);
		}
	}

	return parts.join("\n");
}

// Format table list as markdown
export function formatTableListAsMarkdown(result: ListTablesResult): string {
	if (!result.tables || result.tables.length === 0) {
		return "*No tables found*";
	}

	// Group by schema
	const bySchema: Record<string, TableInfo[]> = {};
	for (const table of result.tables) {
		const schema = table.table_schema || "public";
		if (!bySchema[schema]) {
			bySchema[schema] = [];
		}
		bySchema[schema].push(table);
	}

	const parts: string[] = [];
	parts.push(`**${result.total_tables} tables found**\n`);

	for (const [schema, tables] of Object.entries(bySchema)) {
		if (Object.keys(bySchema).length > 1) {
			parts.push(`#### Schema: ${schema}`);
		}
		parts.push("| Table | Type |");
		parts.push("| --- | --- |");
		for (const table of tables) {
			parts.push(`| \`${table.table_name}\` | ${table.table_type} |`);
		}
		parts.push("");
	}

	return parts.join("\n");
}

// Helper to format cell values
function formatCellValue(value: unknown): string {
	if (value === null || value === undefined) {
		return "-";
	}
	if (typeof value === "object") {
		return JSON.stringify(value);
	}
	return String(value);
}
