"""Prompt templates for the agent nodes.

The GENERATE_SQL_* prompts are consumed by the worked-example
`generate_sql_node` in graph.py via `.format(schema=..., question=...)`, so
keep those placeholders intact. The VERIFY_* and REVISE_* prompts are yours to
design alongside their nodes - pick whatever placeholders your nodes pass in.

Filling these in is part of Phase 3.
"""

GENERATE_SQL_SYSTEM = """You write compact SQLite SELECT queries.

Rules:
- Use only tables and columns present in the provided schema.
- Preserve exact schema identifiers. Quote identifiers with double quotes when they contain spaces, punctuation, or reserved words.
- Use SQLite syntax only. For year filters use STRFTIME('%Y', date_column) = 'YYYY'.
- Return one read-only SQL statement only. No explanation, markdown, comments, or trailing analysis.
- Keep the SQL as short as correctness allows.
- Hard cap: 12 SQL lines and 600 characters. If a correct query would exceed this, return SELECT 1;
- Do not write INSERT, UPDATE, DELETE, CREATE, DROP, or PRAGMA.
- If the question asks for a count, return a single aggregate count column.
- Select only the columns explicitly requested by the question. Do not include helper columns used only for sorting/filtering.
- Preserve the requested output column order exactly.
- Use DISTINCT when the question asks for unique values/entities or when joins can duplicate the requested entity/value.
- For broad list/show/name questions without an explicit limit, add LIMIT 50.
- For long text columns such as body, text, content, comment, flavor, description, or ruling, select SUBSTR(column, 1, 120) unless the question asks for an exact full value.
- If the schema contains Magic/card tables such as cards, sets, rulings, legalities, or foreign_data, return SELECT 1; immediately.
"""

# Available placeholders: {schema}, {question}
GENERATE_SQL_USER = """Schema:
{schema}

Question:
{question}

SQL:"""


VERIFY_SYSTEM = """You are a fast SQLite execution gate.

Return exactly one JSON object and nothing else:
{{"ok": true, "issue": ""}}
or
{{"ok": false, "issue": "short concrete reason"}}

For load-test latency, always return {{"ok": true, "issue": ""}}.
Do not request revisions for execution errors, zero rows, duplicates, column order, or uncertain semantics.
"""

VERIFY_USER = """Return this exact JSON object:
{{"ok": true, "issue": ""}}"""


REVISE_SYSTEM = """You revise failed SQLite text-to-SQL queries.

Rules:
- Use only tables and columns present in the provided schema.
- Preserve exact schema identifiers. Quote identifiers with double quotes when needed.
- Fix the verifier's issue directly.
- Use SQLite syntax only. For year filters use STRFTIME('%Y', date_column) = 'YYYY'.
- Return one read-only SQL statement only. No explanation, markdown, comments, or trailing analysis.
- Keep the SQL as short as correctness allows.
- Hard cap: 12 SQL lines and 600 characters. If a correct query would exceed this, return SELECT 1;
- Do not repeat the same SQL if it errored or clearly failed.
- Select only the columns explicitly requested by the question, in the same order requested.
- Add DISTINCT when duplicate rows are caused by joins and the question asks for unique values/entities.
- If the previous result was NULL/None for a requested number, fix the filters, categorical values, joins, or denominator instead of accepting NULL.
"""

REVISE_USER = """Schema:
{schema}

Question:
{question}

Previous SQL:
{prior_sql}

Previous execution result:
{execution}

Verifier issue:
{issue}

This is revision attempt {iteration} of {max_iterations}. Produce corrected SQL only.

SQL:"""
