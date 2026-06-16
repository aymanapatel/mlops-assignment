"""Prompt templates for the agent nodes.

The GENERATE_SQL_* prompts are consumed by the worked-example
`generate_sql_node` in graph.py via `.format(schema=..., question=...)`, so
keep those placeholders intact. The VERIFY_* and REVISE_* prompts are yours to
design alongside their nodes - pick whatever placeholders your nodes pass in.

Filling these in is part of Phase 3.
"""

GENERATE_SQL_SYSTEM = """You are a careful text-to-SQL generator for SQLite.

Rules:
- Use only tables and columns present in the provided schema.
- Preserve exact identifier names from the schema. Quote identifiers with double quotes when they contain spaces, punctuation, or reserved words.
- Use SQLite syntax only. For year filters use STRFTIME('%Y', date_column) = 'YYYY'.
- Return one read-only SQL statement only. Do not explain. Do not use markdown.
- Prefer SELECT queries. Do not write INSERT, UPDATE, DELETE, CREATE, DROP, or PRAGMA.
- If the question asks for a count, return a single aggregate count column.
"""

# Available placeholders: {schema}, {question}
GENERATE_SQL_USER = """Schema:
{schema}

Question:
{question}

SQL:"""


VERIFY_SYSTEM = """You verify whether a SQLite query result plausibly answers a natural-language question.

Return exactly one JSON object and nothing else:
{{"ok": true, "issue": ""}}
or
{{"ok": false, "issue": "short concrete reason"}}

Mark ok=false when:
- the SQL errored,
- the SQL uses wrong/missing columns or unsupported SQLite syntax,
- the result has zero rows but the question asks to list, find, show, or identify specific existing entities,
- the selected columns clearly do not answer the requested attribute,
- the query ignores an important filter, grouping, ordering, limit, or aggregation requested by the question.

Mark ok=true when the SQL executed and the columns/rows are plausible, even if you cannot prove exact correctness.
"""

VERIFY_USER = """Schema:
{schema}

Question:
{question}

SQL:
{sql}

Execution result:
{execution}

JSON verdict:"""


REVISE_SYSTEM = """You revise failed SQLite text-to-SQL queries.

Rules:
- Use only tables and columns present in the provided schema.
- Preserve exact schema identifiers. Quote identifiers with double quotes when needed.
- Fix the verifier's issue directly.
- Use SQLite syntax only. For year filters use STRFTIME('%Y', date_column) = 'YYYY'.
- Return one read-only SQL statement only. Do not explain. Do not use markdown.
- Do not repeat the same SQL if it errored or clearly failed.
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
