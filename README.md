# Aetheria // Labs — Stripe 2026 E-Commerce & Payment State Machine Reference (`stripe-2026-commerce-reference`)

Flagship reference e-commerce storefront and interactive payment engineering workbench demonstrating Stripe's **2026 (`2026-09-30.acacia`)** payment stack, **Bridge Stablecoin Orchestration**, **13-Step PaymentIntent State Machine Academy**, and **7 Mandatory Production Security Guardrails**.

---

## 1. Architectural Capabilities Demonstrated

| Module | Stripe API / Surface | Key Capabilities |
| :--- | :--- | :--- |
| **01. Flagship Storefront & Adaptive Pricing** | `FX Quotes API` + `Payment Element` | Presentment across 6 global markets (`US`, `DE`, `NL`, `GB`, `TR`, `JP`) with zero-decimal JPY handling and **2026 Subscription FX Stability Buffer** (`2.0%–3.5%`). |
| **02. Optimized Checkout Suite (OCS)** | `POST /v1/payment_intents` · `POST /v1/tax/calculations` | AI-ordered local payment methods, **Link** 1-Click authentication, **Stripe Tax** (`txcd_99999999` vs `txcd_10103001`), EU B2B Reverse Charge VAT (`0%`), **Stripe Radar AI** risk scoring, and **EMV 3D Secure 2.2** step-up modal. |
| **03. Billing & Metronome Usage Meters** | `POST /v1/billing/meter_events` | Real-time high-throughput event ingestion (`neural_dsp_compute_seconds`) with deterministic idempotency keys and live upcoming invoice overage calculation. |
| **04. Connect v2, Issuing, Agentic AI & Bridge Stablecoins** | `POST /v2/core/accounts` · `POST /v1/issuing/cards` · `POST /v1/agentic/order_intents` · `Bridge /v0/liquidation_addresses` & `/v0/transfers` | Multi-vendor split payouts (`transfer_group`), virtual commercial cards with real-time spend controls, AI Agentic single-use Delegated Payment Tokens (`spt_agent_...`), and **Bridge** Stablecoin (`USDC`, `USDB`, `EURC`, `PYUSD` across Base, Solana, Arbitrum, Polygon, Stellar). |
| **05. 13-Step Payment State Machine Academy** | `POST /api/stripe/state_machine/step` | Interactive step-by-step state transitions (`requires_payment_method` &rarr; `requires_confirmation` &rarr; `requires_action` / `processing` / `requires_capture` &rarr; `succeeded` / `canceled` + Bridge Stablecoin settlement) with cURL, Node.js, Python, and Go snippets. |
| **06. Production Guardrails & Security Lab** | `POST /api/stripe/guardrails/test` · `POST /api/stripe/webhooks/receive` | Live interactive verification of the **7 Mandatory Stripe Production Best Practices**. |
| **07. Agentic AI Chatbot (Local LLM)** | `POST /api/stripe/agentic/chat` · `POST /api/stripe/agentic/confirm_order` | Conversational Local LLM shopping assistant (built-in deterministic NLU + optional local Ollama passthrough) executing the **6-Step Stripe Agentic Commerce Protocol (ACP)** pipeline (`mcp.catalog.resolve_skus` &rarr; `/v1/tax/calculations` &rarr; `/v1/agentic/order_intents` &rarr; `spt_agent_...` single-use token &rarr; idempotent `/v1/payment_intents` &rarr; signed webhooks) with Autonomous and Human-in-the-Loop governance modes. |

---

## 2. The 7 Mandatory Production Best Practices Enforced

1. **Zero Trust on Client-Side Amounts**: Never accept `amount` or `price` from browser request bodies (`HTTP 400 zero_trust_client_amount_rejected`). Send only `sku_id + quantity`, look up canonical prices in integer minor units (`84900` cents = `$849.00`) in the server-side `CATALOG`, and compute totals server-side.
2. **Deterministic `Idempotency-Key`s**: Never generate a random `uuid4()` inside a retry loop. Uses deterministic keys tied to the business entity (`f"pi_create_{order_id}_attempt_{attempt_no}"`), caches responses for 24 hours (`86,400s`) to prevent double charges on network drops, and returns `HTTP 400 idempotency_error` if reused with modified parameters.
3. **Raw-Body Cryptographic Webhook Verification (`Stripe-Signature`)**: Validates HMAC-SHA256 over the unparsed raw byte stream (`raw_body`), never a re-serialized JSON dictionary, and enforces a **300-second (5-minute)** timestamp tolerance against replay attacks.
4. **Idempotent & Asynchronous Webhook Fulfillment**: Deduplicates `event.id` (`INSERT INTO processed_events (event_id) VALUES (...) ON CONFLICT DO NOTHING`), pushes fulfillment work to an async background worker queue, and returns `HTTP 200` within `<200ms` (handling Stripe's 72-hour exponential backoff retries and out-of-order delivery).
5. **Granular Stripe Exception Taxonomy**: Explicitly distinguishes `stripe.error.CardError` (`HTTP 402` business decline — never auto-retry; return user-friendly message and increment `attempt_no`) from `stripe.error.RateLimitError` (`HTTP 429`) and `stripe.error.APIConnectionError` (`HTTP 503` — transient errors; auto-retry with exponential backoff + jitter using the **same** `Idempotency-Key`).
6. **Eliminating N+1 API Calls with `expand[]` & Cursor Pagination**: Hydrates `expand=['latest_charge.balance_transaction', 'customer']` in a single HTTP round-trip and supports cursor-based pagination (`starting_after='pi_...'` / `auto_paging_iter()`).
7. **Structured `metadata` Propagation**: Attaches `metadata={'order_id': order_id, 'customer_tier': 'enterprise', 'erp_cost_center': 'IT-01'}` across `PaymentIntent`, `Charge`, `TaxCalculation`, `Transfer`, and `Refund` objects for zero-lookup BigQuery Data Pipeline joins.

---

## 3. Running Locally & Deploying to Vercel

### Local Execution
```bash
python3 server.py
# Open http://localhost:8765
```

### Run End-to-End Integration Tests
```bash
python3 test_server.py
```

### Deploy to Vercel
This repository includes `vercel.json` and `api/index.py` for zero-configuration deployment on Vercel:
1. Push this repository to GitHub (`https://github.com/zichicc/stripe-2026-commerce-reference`).
2. Import `zichicc/stripe-2026-commerce-reference` at [https://vercel.com/new](https://vercel.com/new) and click **Deploy**.
