# What Surprised Me: Week 2 Reflections

---

## dbt Compiles, PostgreSQL Executes

I assumed dbt "runs" SQL directly on the database. Wrong. dbt compiles Jinja2 templates into SQL, then sends compiled queries to PostgreSQL. This single realization changed how I understood the entire framework. When I write `{{ ref('stg_github_events') }}`, dbt doesn't send that to the database—it replaces it with the actual table name during compilation. When I use `{{ source('github_raw_source', 'raw_events') }}`, dbt resolves that to the schema and table defined in `_sources.yml`.

This explains *why* dbt uses macros instead of standard SQL functions. It's not that dbt doesn't understand SQL—it's that dbt adds a layer of logic on top of SQL. Testing that I thought should fail suddenly made sense: dbt's built-in tests are SQL templates. When you add `unique:` to a column, dbt generates the SELECT statement that checks uniqueness. You don't write the test—dbt does. This is powerful because you get consistency and testing patterns for free.

---

## Bronze and Silver Layers Actually Solve Problems

Creating a Bronze layer that's identical to the raw table seemed redundant. Why have both `github_events_raw` and `stg_github_events` if they contain the same data? The answer became obvious during Week 2: Bronze isn't about transforming data—it's about declaring intent.

`_sources.yml` documents where data comes from and when it should be fresh. Auto-generated tests alert us if the upstream source stops providing data. The staging view standardizes column names and types. These are small things individually, but together they create a contract: "This is where external data enters the system."

Silver layers are where business logic happens. `int_push_events` filters to one event type and extracts relevant fields. `int_pull_requests` does the same for another event type. They're independent—a bug in one doesn't cascade to the other. When debugging metrics from the dashboard, I can query Silver to see intermediate results. See something wrong in Silver? Go back to Bronze. Something wrong in Bronze? Check the source. The layers create a debugging chain that's almost impossible with flat transformation.

---

## Automated Tests Are Honest

Before Week 2, I thought comprehensive test suites were for mature projects. "Our data is small—we can verify it manually." Implementing 26 tests early revealed how wrong that thinking was.

Three things stand out:

**Tests catch what visual inspection misses.** A PR event without a `pr_action` field looks fine to humans. The `not_null` test fails. The test is honest—it says "this record is incomplete"—while I would have missed it.

**Tests document what "correct" means.** `push_model_integrity` test verifies only PushEvents reach `int_push_events`. That's a business rule, and it's enforced automatically. A future developer can read that test and understand the model's contract without asking questions.

**Tests give confidence to refactor.** Our commit_count formula uses COALESCE to default to 0. Is that right? The `no_negative_commit_count` test proves it works. If someone changes the logic and it breaks, the test fails immediately. That's the entire point of testing—it lets you be fearless.

---

## JSONB Made Sense

PostgreSQL's JSONB operators (`->`, `->>`, `jsonb_array_length()`) initially felt like obscure syntax. They're not obscure—they're elegant. `raw_payload -> 'actor' ->> 'login'` reads like traversing an object tree, which is exactly what it is. The first operator returns intermediate JSONB structures (so you can keep navigating), the second returns TEXT (when you're done navigating and want the actual value).

Defensive SQL with COALESCE stopped feeling defensive—it became standard. JSONB extraction might return NULL if the field doesn't exist, so COALESCE() defaults to 0 for commit counts. That's not defensive, that's intentional. It's saying "if commits aren't specified, we count zero." That's a business decision, not a hack.

---

## Data Quality Is Political

"Why 26 tests?" a peer asked. Fair question. Tests cost maintenance effort. But consider the alternative: a buggy metric reaches the dashboard, informs a business decision, and nobody catches it until customers complain. That's not just technical debt—that's reputation damage.

The tests we implemented catch issues before they propagate. Future analysts building on top of Silver models can trust those models. They know if something breaks, tests will scream. That trust is worth the maintenance cost. It's the difference between "I think the data is probably correct" and "The data is verified to be correct."

