# MCP Metadata Chatbot: Multi-Agent Discovery & Curation

A conversational chatbot that helps you discover, explore, and enrich your data catalog using OpenMetadata's MCP tools. This cookbook demonstrates **agent-to-agent delegation** — an orchestrator agent routes queries to specialist agents, each with their own tools and expertise.

## Business Problem

**Scenario:** Your data catalog has hundreds of tables, dashboards, and pipelines. Data engineers need to find relevant assets, understand data flows, and keep metadata up to date — but they're scattered across different tools and workflows.

Common questions that are hard to answer today:

1. "Which tables contain customer payment data?" (discovery)
2. "What feeds into the daily revenue dashboard?" (lineage)
3. "These staging tables have no descriptions — can someone fix that?" (curation)
4. "Find all PII tables, show their lineage, and tag them as sensitive" (multi-step)

**Traditional approach:** Jump between the catalog UI, lineage graphs, and documentation tools. Each step is manual and context is lost between tools.

**With the Metadata Chatbot:** Ask a single AI assistant that delegates to specialists — a Discovery agent for search, a Lineage agent for tracing data flow, and a Curator agent for updating metadata — all in one conversation.

## Architecture

```
                         +----------------+
                         |  User Query    |
                         +-------+--------+
                                 |
                        +--------v---------+
                        |  Orchestrator    |
                        |  Agent (GPT-4o)  |
                        +--+-------+----+--+
                           |       |    |
              +------------+       |    +------------+
              |                    |                 |
   +----------v----------+ +------v------+ +--------v--------+
   |  Discovery Agent    | | Lineage     | |  Curator Agent  |
   |                     | | Agent       | |                 |
   | - semantic_search   | | - lineage   | | - patch_entity  |
   | - search_metadata   | | - details   | | - glossary_term |
   | - get_details       | |             | | - get_details   |
   +----------+----------+ +------+------+ +--------+--------+
              |                    |                 |
              +-----------+-------+-----------------+
                          |
                 +--------v--------+
                 |  OpenMetadata   |
                 |  MCP Server     |
                 +-----------------+
```

### How Agent-to-Agent Delegation Works

The chatbot uses a **two-tier agent architecture**:

1. **Orchestrator Agent** — Receives the user's message and decides which specialist(s) to call. It does NOT have direct access to MCP tools. Instead, its "tools" are calls to specialist agents. This separation means:
   - The orchestrator focuses on **routing and synthesis**
   - Each specialist focuses on **deep expertise** with its own MCP tools
   - The orchestrator can **chain** specialists for multi-step tasks

2. **Specialist Agents** — Each is a full LangChain agent with its own system prompt and MCP tools:
   - **Discovery Agent** — `semantic_search`, `search_metadata`, `get_entity_details`
   - **Lineage Agent** — `get_entity_lineage`, `get_entity_details`
   - **Curator Agent** — `patch_entity`, `create_glossary_term`, `get_entity_details`

When the orchestrator calls `discover_metadata("tables related to payments")`, it invokes the Discovery agent, which performs its own multi-step tool-calling loop (search, get details, synthesize). The result flows back to the orchestrator, which can then pass it to the Lineage or Curator agent for the next step.

This pattern is powerful because:
- **Separation of concerns** — Each agent has a focused prompt and toolset
- **Composability** — The orchestrator chains agents for complex workflows
- **Safety** — The Curator agent is the only one with write access
- **Scalability** — Add new specialists without changing existing ones

## Prerequisites

- [Demo Database](../resources/demo-database/) running with data ingested into OpenMetadata
- Python 3.10+
- OpenAI API key (or any LangChain-compatible LLM)

## Installation

```bash
pip install ai-sdk[langchain] langchain langchain-openai
```

## Environment Setup

```bash
# OpenMetadata credentials
export AI_SDK_HOST="https://your-openmetadata.com"
export AI_SDK_TOKEN="..."

# LLM API key
export OPENAI_API_KEY="..."
```

## Running the Chatbot

```bash
python chatbot.py
```

You'll see an interactive prompt:

```
============================================================
  Metadata Chatbot — Multi-Agent Assistant
============================================================

I can help you discover, explore, and enrich your metadata.
Ask me anything about your data catalog!

Examples:
  "Find all tables related to customer data"
  "What feeds into the daily revenue report?"
  "Add a description to the orders staging table"
  "Find undocumented finance tables and describe them"

Type 'quit' to exit.
```

## Example Interactions

### Example 1: Semantic Search & Discovery

**Input:**
```
Find tables related to customer lifetime value
```

**What happens under the hood:**

The orchestrator calls `discover_metadata` with this query. The Discovery agent uses `semantic_search` (not keyword search) to find tables by meaning — even if none contain the exact phrase "lifetime value." It then calls `get_entity_details` on the top results to gather columns, owners, and tags.

**Expected Response:**

```markdown
I found several tables related to customer lifetime value:

## Results

| Table | Schema | Description | Owner |
|-------|--------|-------------|-------|
| [dim_customers](https://host/table/jaffle_shop.public.dim_customers) | marts_core | Customer dimension with lifetime metrics and segmentation | Eve Davis |
| [int_orders__enriched](https://host/table/jaffle_shop.public.int_orders__enriched) | intermediate | Orders enriched with customer info and payment details | Alice Johnson |

### dim_customers
This table contains key lifetime value metrics:
- `lifetime_value` — Total spend across all orders
- `first_order_date` / `most_recent_order_date` — Customer tenure
- `number_of_orders` — Purchase frequency
- `customer_segment` — Derived segmentation (New, Returning, VIP)

### int_orders__enriched
An intermediate model that joins orders with payment data. Used to compute
the lifetime metrics that flow into dim_customers.
```

### Example 2: Lineage Exploration

**Input:**
```
What tables feed into fct_daily_revenue and who owns them?
```

**What happens under the hood:**

The orchestrator calls `explore_lineage` with this query. The Lineage agent calls `get_entity_lineage` on `fct_daily_revenue` to map its upstream sources, then calls `get_entity_details` on each node to get owner information.

**Expected Response:**

```markdown
## Upstream Sources of fct_daily_revenue

The daily revenue fact table is built from a chain of transformations:

### Direct Source
- [int_orders__enriched](https://host/table/jaffle_shop.intermediate.int_orders__enriched)
  — Owner: Alice Johnson
  — Joins orders with payments and customer data

### Indirect Sources (2 hops)
- [stg_jaffle_shop__orders](https://host/table/jaffle_shop.staging.stg_jaffle_shop__orders)
  — Owner: Alice Johnson
  — Cleans raw order data from the source system

- [stg_stripe__payments](https://host/table/jaffle_shop.staging.stg_stripe__payments)
  — Owner: Alice Johnson
  — Cleans raw payment transactions from Stripe

### Raw Sources (3 hops)
- [raw_jaffle_shop.orders](https://host/table/jaffle_shop.public.raw_orders)
  — Owner: data-engineering@jaffle.shop
  — Raw orders from the Jaffle Shop application database

- [raw_stripe.payments](https://host/table/jaffle_shop.public.raw_payments)
  — Owner: data-engineering@jaffle.shop
  — Raw payment records from the Stripe API

## Data Flow

raw_orders --> stg_jaffle_shop__orders --+
                                         +--> int_orders__enriched --> fct_daily_revenue
raw_payments --> stg_stripe__payments --+

## Downstream Consumers

No tables or dashboards consume fct_daily_revenue downstream — it is a
terminal mart used directly for reporting.
```

### Example 3: Metadata Update

**Input:**
```
The stg_jaffle_shop__orders table has no description. Add one that says
"Staging model that cleans and standardizes raw order data from the Jaffle
Shop application database."
```

**What happens under the hood:**

The orchestrator calls `update_metadata`. The Curator agent first calls `get_entity_details` to inspect the current metadata (confirming there's no existing description), then calls `patch_entity` to add the description.

**Expected Response:**

```markdown
## Metadata Update Applied

**Entity:** [stg_jaffle_shop__orders](https://host/table/jaffle_shop.staging.stg_jaffle_shop__orders)

**Change:**
- **Description** (was empty):
  "Staging model that cleans and standardizes raw order data from the Jaffle
  Shop application database."

The update was applied successfully. The table now has a description visible
in the OpenMetadata catalog.
```

### Example 4: Multi-Agent Chaining

This is where agent-to-agent delegation shines. A single user request triggers multiple specialists working in sequence.

**Input:**
```
Find all staging tables that don't have descriptions and add appropriate
descriptions based on their columns and lineage.
```

**What happens under the hood:**

1. The orchestrator calls `discover_metadata` with "staging tables without descriptions"
2. The Discovery agent searches for staging tables and checks which lack descriptions
3. For each undocumented table, the orchestrator calls `explore_lineage` to understand its role
4. Finally, the orchestrator calls `update_metadata` for each table with a generated description

**Expected Response:**

```markdown
I found 2 staging tables without descriptions and updated them:

## 1. stg_stripe__payments

**Lineage context:** Transforms raw Stripe payment records into a clean
staging model. Feeds into int_orders__enriched, then fct_orders and
fct_daily_revenue.

**Description added:**
"Staging model that cleans and standardizes raw payment transactions from
the Stripe API. Extracts payment status, amount, and method fields for
downstream order enrichment."

## 2. stg_jaffle_shop__customers

**Lineage context:** Transforms raw customer records from the Jaffle Shop
application database. Feeds into dim_customers.

**Description added:**
"Staging model that cleans and deduplicates raw customer records from the
Jaffle Shop application database. Standardizes name and email fields for
the customer dimension table."

---

Both tables now have descriptions in the catalog. The descriptions were
generated based on each table's columns and position in the lineage graph.
```

## Programmatic Usage

You can use the chatbot programmatically instead of the interactive REPL:

```python
from chatbot import create_chatbot, chat

orchestrator, client = create_chatbot()

try:
    # Single question
    response = chat(orchestrator, "Find tables related to payments")
    print(response)

    # Multi-turn (each call is independent — no conversation memory)
    response = chat(orchestrator, "Show lineage for stg_stripe__payments")
    print(response)
finally:
    client.close()
```

## Configuration Options

### Using Different LLMs

The chatbot uses LangChain, so you can swap in any compatible LLM. Edit the `_create_specialist` function and the orchestrator creation in `create_chatbot()`:

```python
# Claude (via Amazon Bedrock)
from langchain_aws import ChatBedrock

agent = create_agent(
    model=ChatBedrock(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name="us-east-1"
    ),
    tools=tools,
    system_prompt=prompt,
)

# Local LLM (via Ollama)
from langchain_ollama import ChatOllama

agent = create_agent(
    model=ChatOllama(model="llama3.1:70b"),
    tools=tools,
    system_prompt=prompt,
)

# Azure OpenAI
from langchain_openai import AzureChatOpenAI

agent = create_agent(
    model=AzureChatOpenAI(
        deployment_name="gpt-4",
        api_version="2024-02-15-preview"
    ),
    tools=tools,
    system_prompt=prompt,
)
```

### Restricting Write Access

If you want a read-only chatbot (no metadata updates), remove the Curator agent from the orchestrator:

```python
def create_chatbot():
    config = AiSdkConfig.from_env()
    client = AiSdk.from_config(config)
    host = config.host.rstrip("/")

    discovery = _create_specialist(
        client,
        tools=[MCPTool.SEMANTIC_SEARCH, MCPTool.SEARCH_METADATA, MCPTool.GET_ENTITY_DETAILS],
        system_prompt=DISCOVERY_PROMPT.format(metadata_host=host),
    )

    lineage = _create_specialist(
        client,
        tools=[MCPTool.GET_ENTITY_LINEAGE, MCPTool.GET_ENTITY_DETAILS],
        system_prompt=LINEAGE_PROMPT.format(metadata_host=host),
    )

    # Only discovery + lineage — no write tools
    orchestrator_tools = [
        DiscoverMetadataTool(specialist=discovery),
        ExploreLineageTool(specialist=lineage),
    ]

    orchestrator = create_agent(
        model="openai:gpt-4o",
        tools=orchestrator_tools,
        system_prompt=ORCHESTRATOR_PROMPT,
    )

    return orchestrator, client
```

### Adding a New Specialist

The architecture is designed to be extensible. To add a new specialist (e.g., Data Quality):

```python
DQ_PROMPT = """You are a Data Quality specialist..."""

def create_chatbot():
    # ... existing specialists ...

    dq_agent = _create_specialist(
        client,
        tools=[
            MCPTool.GET_TEST_DEFINITIONS,
            MCPTool.CREATE_TEST_CASE,
            MCPTool.ROOT_CAUSE_ANALYSIS,
        ],
        system_prompt=DQ_PROMPT.format(metadata_host=host),
    )

    orchestrator_tools = [
        DiscoverMetadataTool(specialist=discovery),
        ExploreLineageTool(specialist=lineage),
        UpdateMetadataTool(specialist=curator),
        DataQualityTool(specialist=dq_agent),  # New specialist
    ]
    # ...
```

The orchestrator's system prompt will automatically discover the new tool's name and description and start routing appropriate queries to it.

## How It Compares to Single-Agent Approaches

| Aspect | Single Agent | Multi-Agent (this cookbook) |
|--------|-------------|--------------------------|
| Tool count | All tools in one agent | 2-3 tools per specialist |
| Prompt length | Long, covers everything | Short, focused per specialist |
| Error handling | One failure stops all | Specialists fail independently |
| Write safety | All tools available always | Only Curator has write access |
| Extensibility | Add tools to one prompt | Add a new specialist agent |
| Debugging | Hard to trace which tool failed | Clear which specialist was called |

The multi-agent pattern trades a small amount of latency (orchestrator to specialist round trip) for much better separation of concerns and safety.
