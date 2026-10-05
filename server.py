#!/usr/bin/env python3
"""Aetheria Labs — Flagship E-Commerce Demo Store & Stripe Payment Layer API Server.

Showcases Stripe's latest (2026) payment technologies and API integrations:
  - Optimized Checkout Suite (Payment Element, Express Checkout Element, Link, Address Element)
  - Adaptive Pricing & FX Quotes API (/v1/fx_quotes) with Subscription Stability Buffer
  - Stripe Tax API (/v1/tax/calculations & /v1/tax/transactions) with B2B Reverse Charge VAT
  - Stripe Radar AI Risk Scoring & EMV 3D Secure 2 (3DS2) Step-Up Authentication
  - Stripe Billing Subscriptions (/v1/subscriptions) & Metronome Usage Meters (/v1/billing/meter_events)
  - Stripe Connect Accounts v2 (/v2/core/accounts) Multi-Vendor Split Payments & Application Fees
  - Stripe Financial Connections (Instant Bank Pay) & USDC Stablecoin Crypto Checkout
  - Stripe Agentic Commerce Toolkit (/v1/agentic/order_intents & Delegated Payment Tokens)
  - Live Webhook Event Stream with HMAC-SHA256 Stripe-Signature generation & Live API passthrough
"""

import datetime
import hashlib
import hmac
import http.server
import json
import os
import random
import re
import socketserver
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PORT = int(os.environ.get("PORT", "8765"))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
STRIPE_API_VERSION = "2026-09-30.acacia"
WEBHOOK_SECRET = "whsec_aetheria_demo_9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c"

# Runtime configuration (supports switching to live Stripe test keys at runtime)
RUNTIME_CONFIG: dict[str, Any] = {
    "mode": "sandbox_simulator",  # "sandbox_simulator" or "live_stripe_api"
    "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_51Q9AetheriaLabsDemoStoreKey0001"),
    "secret_key": os.environ.get("STRIPE_SECRET_KEY", ""),
    "api_version": STRIPE_API_VERSION,
    "webhook_secret": WEBHOOK_SECRET,
}

# Product Catalog spanning Physical Hardware, SaaS + Usage Metering, and Connect Marketplace
CATALOG: list[dict[str, Any]] = [
    {
        "id": "prod_synth_mk2",
        "price_id": "price_1Q9SynthMk2USD",
        "name": "Aetheria Field Synthesizer MK-II",
        "subtitle": "Polyphonic Tactile Workstation & 32-bit Float Recorder",
        "category": "Flagship Hardware",
        "commerce_model": "one_time",
        "stripe_features": ["Payment Element", "Express Checkout", "Klarna / Affirm BNPL", "Stripe Tax"],
        "unit_amount_usd": 84900,  # $849.00
        "tax_code": "txcd_99999999",  # Tangible personal property
        "tax_code_label": "Physical Hardware (txcd_99999999)",
        "image": "/images/synth_mk2.jpg",
        "badge": "Flagship Direct",
        "specs": ["CNC Anodized Aluminum", "OLED Waveform Display", "MPE Velocity Keys", "USB-C / MIDI / CV"],
        "seller": None,
    },
    {
        "id": "prod_monolith_console",
        "price_id": "price_1Q9MonolithConsoleUSD",
        "name": "Monolith Tactile Mastering Console",
        "subtitle": "Motorized Fader Surface & Precision Analog Summing Controller",
        "category": "Flagship Hardware",
        "commerce_model": "one_time",
        "stripe_features": ["Link 1-Click", "Adaptive Pricing", "Instant Bank Pay (ACH/SEPA)", "Radar AI"],
        "unit_amount_usd": 54000,  # $540.00
        "tax_code": "txcd_99999999",
        "tax_code_label": "Physical Hardware (txcd_99999999)",
        "image": "/images/studio_controller.jpg",
        "badge": "Studio Hardware",
        "specs": ["100mm Motorized Alps Faders", "American Walnut Sides", "Knurled Steel Master Dial", "Thunderbolt 4"],
        "seller": None,
    },
    {
        "id": "prod_planar_headphones",
        "price_id": "price_1Q9PlanarHeadphonesUSD",
        "name": "Aetheria Reference Planar Headphones",
        "subtitle": "Open-Back CNC Titanium Acoustic Reference Monitors",
        "category": "Flagship Hardware",
        "commerce_model": "one_time",
        "stripe_features": ["Express Checkout", "USDC Stablecoin Pay", "3DS2 Step-Up", "Stripe Tax"],
        "unit_amount_usd": 69000,  # $690.00
        "tax_code": "txcd_99999999",
        "tax_code_label": "Physical Hardware (txcd_99999999)",
        "image": "/images/spatial_headphones.jpg",
        "badge": "Reference Audio",
        "specs": ["98mm Planar Magnetic Driver", "Grade-5 Titanium Earcups", "Perforated Lambskin Pads", "OCC Braided Cable"],
        "seller": None,
    },
    {
        "id": "prod_neural_cloud_pro",
        "price_id": "price_1Q9NeuralCloudProMonthly",
        "name": "Neural Stem & Spatial Cloud Suite",
        "subtitle": "Hardware DSP Key + Recurring Cloud Subscription & Usage Metering",
        "category": "Stripe Billing + Metronome",
        "commerce_model": "subscription_metered",
        "stripe_features": ["Stripe Billing", "Metronome Usage Meters", "FX Stability Buffer", "Digital SaaS Tax"],
        "unit_amount_usd": 3900,  # $39.00 / month base
        "recurring_interval": "month",
        "metered_rate_usd_cents_per_100s": 40,  # $0.004 / DSP second ($0.40 per 100s) above 5,000 included sec
        "included_units": 5000,
        "meter_event_name": "neural_dsp_compute_seconds",
        "tax_code": "txcd_10000000",  # Electronically supplied SaaS
        "tax_code_label": "Cloud SaaS & Compute (txcd_10000000)",
        "image": "/images/cloud_stem_engine.jpg",
        "badge": "Recurring + Metered",
        "specs": ["$39/mo Base + 5,000 DSP Sec", "$0.004/sec Overages (Billing Meters)", "FX Stability Buffer (3.5%)", "Zero-Latency Stem Isolation"],
        "seller": None,
    },
    {
        "id": "prod_ambernex_dsp",
        "price_id": "price_1Q9AmberNexDSPUSD",
        "name": "AmberNex Euro-DSP Effects Unit",
        "subtitle": "Boutique Granular Reverb & CV Matrix Processor",
        "category": "Connect Marketplace",
        "commerce_model": "connect_split",
        "stripe_features": ["Connect Accounts v2", "12% Platform Fee", "Automated Split Payout", "Managed Risk"],
        "unit_amount_usd": 42000,  # $420.00
        "tax_code": "txcd_99999999",
        "tax_code_label": "Partner Hardware (txcd_99999999)",
        "image": "/images/modular_dsp.jpg",
        "badge": "Connect Partner · DE",
        "specs": ["Brushed Titanium Chassis", "Warm Amber LED Meter Bar", "4x CV Patch I/O", "Hand-Built in Berlin"],
        "seller": {
            "account_id": "acct_2V9klangwerkBerlin",
            "name": "Klangwerk Berlin GmbH",
            "country": "DE",
            "commission_rate": 0.12,
            "api_version": "v2/core/accounts",
            "payout_schedule": "Daily Automatic (T+2 EUR)",
        },
    },
    {
        "id": "prod_kyoto_mic",
        "price_id": "price_1Q9KyotoMicUSD",
        "name": "Kyoto Acoustics Binaural Field Mic",
        "subtitle": "Matched Brass-Capsule 3D Stereo Condenser Microphone",
        "category": "Connect Marketplace",
        "commerce_model": "connect_split",
        "stripe_features": ["Connect Accounts v2", "Cross-Border Payout", "12% Platform Fee", "Destination Charge"],
        "unit_amount_usd": 38000,  # $380.00
        "tax_code": "txcd_99999999",
        "tax_code_label": "Partner Hardware (txcd_99999999)",
        "image": "/images/field_mic.jpg",
        "badge": "Connect Partner · JP",
        "specs": ["Dual Machined Brass Capsules", "Ultra-Low 7dBA Self-Noise", "Titanium Mini Tripod", "Crafted in Kyoto"],
        "seller": {
            "account_id": "acct_2V9kyotoAcoustics",
            "name": "Kyoto Acoustics KK",
            "country": "JP",
            "commission_rate": 0.12,
            "api_version": "v2/core/accounts",
            "payout_schedule": "Weekly Automatic (JPY)",
        },
    },
]

CATALOG_BY_ID: dict[str, dict[str, Any]] = {p["id"]: p for p in CATALOG}

# Adaptive Pricing & Regional Payment Method Profiles (Stripe Optimized Checkout Suite)
LOCALE_PROFILES: dict[str, dict[str, Any]] = {
    "US": {
        "country": "US",
        "name": "United States",
        "currency": "usd",
        "symbol": "$",
        "fx_rate": 1.0,
        "zero_decimal": False,
        "fx_spread_bps": 0,
        "stability_buffer_pct": 0.0,
        "tax_name": "US State Sales Tax (NY 8.875%)",
        "tax_rate_physical": 0.08875,
        "tax_rate_digital": 0.08875,
        "tax_jurisdiction": "State of New York, US",
        "shipping_flat_usd_cents": 0,
        "ai_ordered_methods": [
            {"id": "link", "label": "Link (1-Click Instant)", "type": "wallet", "badge": "Fastest · 94% Conv."},
            {"id": "card", "label": "Card (Visa, Mastercard, Amex)", "type": "card", "badge": "Network Tokenized"},
            {"id": "crypto_bridge", "label": "Bridge Stablecoins (USDC / USDB / EURC)", "type": "crypto", "badge": "Bridge · 0.5% Fee · Instant L2"},
            {"id": "us_bank_account", "label": "Instant Bank Pay (Financial Connections)", "type": "bank", "badge": "0.8% Fee ($5 Cap)"},
            {"id": "affirm", "label": "Affirm (4 interest-free or monthly)", "type": "bnpl", "badge": "BNPL · Up to $17.5k"},
            {"id": "klarna", "label": "Klarna (Pay in 4)", "type": "bnpl", "badge": "BNPL · 0% APR"},
        ],
        "express_wallets": ["Link", "Bridge USDC/USDB", "Apple Pay", "Google Pay"],
    },
    "DE": {
        "country": "DE",
        "name": "Germany (EU)",
        "currency": "eur",
        "symbol": "€",
        "fx_rate": 0.92,
        "zero_decimal": False,
        "fx_spread_bps": 120,
        "stability_buffer_pct": 2.0,
        "tax_name": "EU Mehrwertsteuer (MwSt 19%)",
        "tax_rate_physical": 0.19,
        "tax_rate_digital": 0.19,
        "tax_jurisdiction": "Bundesrepublik Deutschland (EU OSS)",
        "shipping_flat_usd_cents": 1800,
        "ai_ordered_methods": [
            {"id": "klarna", "label": "Klarna (Rechnung & Ratenkauf)", "type": "bnpl", "badge": "#1 in DE"},
            {"id": "sepa_debit", "label": "SEPA-Lastschrift (IBAN Direct Debit)", "type": "bank", "badge": "EU Bank Standard"},
            {"id": "crypto_bridge", "label": "Bridge Stablecoins (EURC / USDC / USDB)", "type": "crypto", "badge": "Bridge · MiCA Compliant"},
            {"id": "link", "label": "Link (1-Click Instant)", "type": "wallet", "badge": "Accelerated"},
            {"id": "card", "label": "Kreditkarte / Debitkarte (3DS2)", "type": "card", "badge": "PSD2 SCA Ready"},
            {"id": "paypal", "label": "PayPal Express", "type": "wallet", "badge": "EU Wallet"},
        ],
        "express_wallets": ["Link", "Bridge EURC/USDC", "Apple Pay", "Google Pay"],
    },
    "NL": {
        "country": "NL",
        "name": "Netherlands (EU)",
        "currency": "eur",
        "symbol": "€",
        "fx_rate": 0.92,
        "zero_decimal": False,
        "fx_spread_bps": 120,
        "stability_buffer_pct": 2.0,
        "tax_name": "NL Belasting Toegevoegde Waarde (BTW 21%)",
        "tax_rate_physical": 0.21,
        "tax_rate_digital": 0.21,
        "tax_jurisdiction": "Netherlands Belastingdienst (EU OSS)",
        "shipping_flat_usd_cents": 1500,
        "ai_ordered_methods": [
            {"id": "ideal", "label": "iDEAL | Wero (Instant Dutch Bank)", "type": "bank", "badge": "70%+ NL Market Share"},
            {"id": "crypto_bridge", "label": "Bridge Stablecoins (EURC / USDC / USDB)", "type": "crypto", "badge": "Bridge · Auto-EUR Settlement"},
            {"id": "link", "label": "Link (1-Click Instant)", "type": "wallet", "badge": "Accelerated"},
            {"id": "klarna", "label": "Klarna (Betaal later)", "type": "bnpl", "badge": "BNPL · 30 Days"},
            {"id": "card", "label": "Card (Visa / Mastercard)", "type": "card", "badge": "PSD2 SCA"},
            {"id": "bancontact", "label": "Bancontact (Benelux)", "type": "bank", "badge": "Instant Debit"},
        ],
        "express_wallets": ["iDEAL Express", "Bridge EURC/USDC", "Link", "Apple Pay"],
    },
    "GB": {
        "country": "GB",
        "name": "United Kingdom",
        "currency": "gbp",
        "symbol": "£",
        "fx_rate": 0.78,
        "zero_decimal": False,
        "fx_spread_bps": 140,
        "stability_buffer_pct": 2.5,
        "tax_name": "UK Value Added Tax (VAT 20%)",
        "tax_rate_physical": 0.20,
        "tax_rate_digital": 0.20,
        "tax_jurisdiction": "HM Revenue & Customs (HMRC UK)",
        "shipping_flat_usd_cents": 1500,
        "ai_ordered_methods": [
            {"id": "link", "label": "Link (1-Click Instant)", "type": "wallet", "badge": "Fastest"},
            {"id": "pay_by_bank", "label": "Pay by Bank (UK Open Banking / Faster Payments)", "type": "bank", "badge": "Instant · No Card Fees"},
            {"id": "crypto_bridge", "label": "Bridge Stablecoins (USDC / USDB -> GBP)", "type": "crypto", "badge": "Bridge · Instant GBP Liquidation"},
            {"id": "card", "label": "Debit / Credit Card (UK 3DS2)", "type": "card", "badge": "Network Tokenized"},
            {"id": "clearpay", "label": "Clearpay (Pay in 4)", "type": "bnpl", "badge": "UK BNPL"},
            {"id": "klarna", "label": "Klarna (Pay in 3)", "type": "bnpl", "badge": "0% Interest"},
        ],
        "express_wallets": ["Link", "Bridge USDC/USDB", "Apple Pay", "Google Pay"],
    },
    "TR": {
        "country": "TR",
        "name": "Türkiye",
        "currency": "try",
        "symbol": "₺",
        "fx_rate": 34.80,
        "zero_decimal": False,
        "fx_spread_bps": 200,
        "stability_buffer_pct": 4.5,
        "tax_name": "Katma Değer Vergisi (KDV 20%)",
        "tax_rate_physical": 0.20,
        "tax_rate_digital": 0.20,
        "tax_jurisdiction": "Gelir İdaresi Başkanlığı (GİB TR)",
        "shipping_flat_usd_cents": 2200,
        "ai_ordered_methods": [
            {"id": "card", "label": "Kredi / Banka Kartı (Taksit & 3DS2)", "type": "card", "badge": "Local Acquiring · 3DS2"},
            {"id": "crypto_bridge", "label": "Bridge Stablecoins (USDC / USDB on Base & Solana)", "type": "crypto", "badge": "Bridge · Zero FX Slippage"},
            {"id": "link", "label": "Link (1-Click Instant)", "type": "wallet", "badge": "Saved Credentials"},
        ],
        "express_wallets": ["Link", "Bridge USDC/USDB", "Apple Pay", "Google Pay"],
    },
    "JP": {
        "country": "JP",
        "name": "Japan",
        "currency": "jpy",
        "symbol": "¥",
        "fx_rate": 152.0,
        "zero_decimal": True,
        "fx_spread_bps": 150,
        "stability_buffer_pct": 2.5,
        "tax_name": "Japanese Consumption Tax (JCT 10%)",
        "tax_rate_physical": 0.10,
        "tax_rate_digital": 0.10,
        "tax_jurisdiction": "National Tax Agency Japan (Qualified Invoice JCT)",
        "shipping_flat_usd_cents": 2000,
        "ai_ordered_methods": [
            {"id": "paypay", "label": "PayPay (QR Instant Wallet)", "type": "wallet", "badge": "#1 JP Digital Wallet"},
            {"id": "crypto_bridge", "label": "Bridge Stablecoins (USDC / USDB -> JPY)", "type": "crypto", "badge": "Bridge · Instant L2 Settlement"},
            {"id": "card", "label": "Credit Card (JCB, Visa, Mastercard)", "type": "card", "badge": "EMV 3DS2"},
            {"id": "konbini", "label": "Konbini (7-Eleven, Lawson, FamilyMart)", "type": "voucher", "badge": "Cash Voucher"},
            {"id": "link", "label": "Link (1-Click Instant)", "type": "wallet", "badge": "Accelerated"},
        ],
        "express_wallets": ["PayPay", "Bridge USDC/USDB", "Apple Pay", "Link"],
    },
}

# In-memory telemetry & state for live inspection
WEBHOOK_EVENTS: list[dict[str, Any]] = []
API_LOGS: list[dict[str, Any]] = []
PAYMENT_INTENTS_STORE: dict[str, dict[str, Any]] = {}
IDEMPOTENCY_STORE: dict[str, dict[str, Any]] = {}
PROCESSED_WEBHOOK_EVENTS: dict[str, dict[str, Any]] = {}
ASYNC_FULFILLMENT_QUEUE: list[dict[str, Any]] = []
METER_USAGE_STATE: dict[str, Any] = {
    "meter_id": "mtr_1Q9NeuralDSPComputeSec",
    "event_name": "neural_dsp_compute_seconds",
    "customer_id": "cus_Q9AetheriaDemoStudio",
    "subscription_id": "sub_1Q9NeuralCloudProActive",
    "included_seconds": 5000,
    "current_period_seconds": 3850,
    "rate_usd_cents_per_100s": 40,  # $0.004/sec
    "events": [
        {
            "id": "mtev_1Q9InitSession01",
            "timestamp": int(time.time()) - 3600,
            "value": 2400,
            "workload": "8-Track Drum & Vocal Stem Isolation (96kHz)",
            "idempotency_key": "idem_stem_sep_96k_01",
        },
        {
            "id": "mtev_1Q9InitSession02",
            "timestamp": int(time.time()) - 1400,
            "value": 1450,
            "workload": "Dolby Atmos 7.1.4 Binaural Downmix Render",
            "idempotency_key": "idem_binaural_render_02",
        },
    ],
}


def gen_stripe_id(prefix: str, length: int = 24) -> str:
    chars = string.ascii_letters + string.digits
    suffix = "".join(random.choices(chars, k=length))
    return f"{prefix}_{suffix}"


def compute_stripe_signature(payload_str: str, secret: str = WEBHOOK_SECRET, custom_ts: int | None = None) -> str:
    ts = custom_ts if custom_ts is not None else int(time.time())
    signed_payload = f"{ts}.{payload_str}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest},v0=6ffbb59b2300aae63f272406069a9788598b792a944a07aba816edb039989a39"


def verify_stripe_webhook_raw_body(
    raw_body: bytes,
    sig_header: str,
    secret: str = WEBHOOK_SECRET,
    tolerance_sec: int = 300,
) -> dict[str, Any]:
    """Validates Stripe-Signature over unparsed raw bytes + enforces 300s timestamp replay tolerance."""
    parts = dict(item.split("=", 1) for item in sig_header.split(",") if "=" in item)
    ts_str = parts.get("t", "0")
    v1_sig = parts.get("v1", "")
    try:
        ts_val = int(ts_str)
    except ValueError:
        return {"verified": False, "code": "invalid_timestamp", "message": "Malformed timestamp in Stripe-Signature header."}

    now_ts = int(time.time())
    age_sec = abs(now_ts - ts_val)
    if age_sec > tolerance_sec:
        return {
            "verified": False,
            "code": "timestamp_out_of_tolerance",
            "age_seconds": age_sec,
            "tolerance_seconds": tolerance_sec,
            "message": f"Webhook timestamp ({ts_val}) is {age_sec}s old, exceeding the {tolerance_sec}s (5-min) replay protection window.",
        }

    signed_payload = f"{ts_val}.".encode("utf-8") + raw_body
    expected_v1 = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_v1, v1_sig):
        return {
            "verified": False,
            "code": "hmac_signature_mismatch",
            "expected_v1_prefix": expected_v1[:16] + "...",
            "received_v1_prefix": v1_sig[:16] + "...",
            "message": "HMAC-SHA256 digest mismatch! Ensure you pass the unparsed raw request bytes (never a re-serialized JSON dict) to construct_event().",
        }

    return {
        "verified": True,
        "code": "hmac_verified_raw_bytes",
        "age_seconds": age_sec,
        "tolerance_seconds": tolerance_sec,
        "signature_v1_prefix": expected_v1[:16] + "...",
        "message": f"Cryptographic HMAC-SHA256 verified over raw byte stream ({len(raw_body)} bytes) within {tolerance_sec}s replay window.",
    }


def emit_webhook_event(event_type: str, data_object: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
    evt_id = gen_stripe_id("evt_3Q9", 21)
    created_ts = int(time.time())
    event_payload = {
        "id": evt_id,
        "object": "event",
        "api_version": RUNTIME_CONFIG["api_version"],
        "created": created_ts,
        "type": event_type,
        "livemode": False,
        "pending_webhooks": 1,
        "request": {
            "id": request_id or gen_stripe_id("req", 14),
            "idempotency_key": gen_stripe_id("idem", 16),
        },
        "data": {
            "object": data_object,
        },
    }
    raw_json = json.dumps(event_payload)
    sig_header = compute_stripe_signature(raw_json)
    record = {
        "id": evt_id,
        "type": event_type,
        "created": created_ts,
        "created_iso": datetime.datetime.fromtimestamp(created_ts, tz=datetime.timezone.utc).strftime("%H:%M:%S.%f")[:-3] + " UTC",
        "stripe_signature": sig_header,
        "payload": event_payload,
        "http_status": 200,
    }
    WEBHOOK_EVENTS.insert(0, record)
    if len(WEBHOOK_EVENTS) > 50:
        WEBHOOK_EVENTS.pop()
    return record


def record_api_log(
    method: str,
    endpoint: str,
    request_body: dict[str, Any],
    response_body: dict[str, Any],
    status_code: int = 200,
    latency_ms: int = 118,
    curl_snippet: str = "",
) -> dict[str, Any]:
    req_id = gen_stripe_id("req", 14)
    entry = {
        "id": req_id,
        "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S.%f")[:-3] + " UTC",
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "api_version": RUNTIME_CONFIG["api_version"],
        "mode": RUNTIME_CONFIG["mode"],
        "request_body": request_body,
        "response_body": response_body,
        "curl_snippet": curl_snippet,
    }
    API_LOGS.insert(0, entry)
    if len(API_LOGS) > 40:
        API_LOGS.pop()
    return entry


def convert_usd_cents_to_local(usd_cents: int, locale_code: str) -> int:
    profile = LOCALE_PROFILES.get(locale_code, LOCALE_PROFILES["US"])
    rate = profile["fx_rate"]
    if profile["zero_decimal"]:
        # e.g. JPY: $849.00 (84900 cents) -> 849 * 152 = 129048 JPY
        return int(round((usd_cents / 100.0) * rate))
    return int(round(usd_cents * rate))


def format_currency_amount(amount_minor: int, locale_code: str) -> str:
    profile = LOCALE_PROFILES.get(locale_code, LOCALE_PROFILES["US"])
    symbol = profile["symbol"]
    if profile["zero_decimal"]:
        return f"{symbol}{amount_minor:,}"
    return f"{symbol}{amount_minor / 100.0:,.2f}"


def calculate_cart_pricing_and_tax(
    items: list[dict[str, Any]],
    locale_code: str,
    vat_id: str = "",
    postal_code: str = "10001",
    apply_stability_buffer: bool = True,
) -> dict[str, Any]:
    profile = LOCALE_PROFILES.get(locale_code, LOCALE_PROFILES["US"])
    vat_clean = vat_id.strip().upper()
    # EU Reverse Charge applies if DE or NL customer supplies a valid EU VAT number (e.g., DE..., NL..., IT..., FR...)
    is_eu_reverse_charge = (
        locale_code in ("DE", "NL")
        and len(vat_clean) >= 8
        and vat_clean[:2].isalpha()
    )

    line_items_detail = []
    subtotal_local = 0
    subtotal_usd_cents = 0
    total_tax_local = 0
    has_subscription = False
    has_physical = False
    connect_transfers = []

    for cart_item in items:
        prod_id = cart_item.get("id")
        qty = max(1, int(cart_item.get("quantity", 1)))
        prod = next((p for p in CATALOG if p["id"] == prod_id), None)
        if not prod:
            continue

        unit_usd = prod["unit_amount_usd"]
        unit_local = convert_usd_cents_to_local(unit_usd, locale_code)

        # If subscription and stability buffer enabled in non-USD currency
        buffer_applied_bps = 0
        if prod["commerce_model"] == "subscription_metered" and apply_stability_buffer and locale_code != "US":
            has_subscription = True
            buffer_applied_bps = int(profile["stability_buffer_pct"] * 100)
        elif prod["commerce_model"] == "subscription_metered":
            has_subscription = True

        if prod["tax_code"] == "txcd_99999999":
            has_physical = True

        line_sub_local = unit_local * qty
        line_sub_usd = unit_usd * qty
        subtotal_local += line_sub_local
        subtotal_usd_cents += line_sub_usd

        # Tax calculation per product tax code
        if is_eu_reverse_charge:
            tax_rate = 0.0
            tax_reason = "reverse_charge"
        else:
            tax_rate = (
                profile["tax_rate_Digital"]
                if "tax_rate_Digital" in profile
                else (
                    profile["tax_rate_digital"]
                    if prod["tax_code"] == "txcd_10000000"
                    else profile["tax_rate_physical"]
                )
            )
            tax_reason = "standard_rated"

        line_tax_local = int(round(line_sub_local * tax_rate))
        total_tax_local += line_tax_local

        # Connect Split calculation if sold by a partner
        if prod.get("seller"):
            seller = prod["seller"]
            gross_local = line_sub_local
            stripe_fee_local = int(round(gross_local * 0.029 + (0 if profile["zero_decimal"] else 30)))
            app_fee_local = int(round(gross_local * seller["commission_rate"]))
            net_transfer_local = max(0, gross_local - app_fee_local)
            connect_transfers.append({
                "product_id": prod["id"],
                "product_name": prod["name"],
                "destination_account": seller["account_id"],
                "seller_name": seller["name"],
                "seller_country": seller["country"],
                "gross_amount": gross_local,
                "stripe_processing_fee_est": stripe_fee_local,
                "application_fee_amount": app_fee_local,
                "net_transfer_amount": net_transfer_local,
                "currency": profile["currency"],
            })

        line_items_detail.append({
            "id": gen_stripe_id("tax_li", 14),
            "product_id": prod["id"],
            "price_id": prod["price_id"],
            "name": prod["name"],
            "commerce_model": prod["commerce_model"],
            "quantity": qty,
            "unit_amount": unit_local,
            "amount": line_sub_local,
            "amount_tax": line_tax_local,
            "tax_code": prod["tax_code"],
            "tax_rate_pct": round(tax_rate * 100, 3),
            "taxability_reason": tax_reason,
            "stability_buffer_bps": buffer_applied_bps,
            "seller": prod.get("seller"),
        })

    shipping_local = convert_usd_cents_to_local(profile["shipping_flat_usd_cents"], locale_code) if has_physical else 0
    shipping_tax_local = 0 if is_eu_reverse_charge else int(round(shipping_local * profile["tax_rate_physical"]))
    total_tax_local += shipping_tax_local
    grand_total_local = subtotal_local + shipping_local + total_tax_local

    tax_calc_id = gen_stripe_id("taxcalc_1Q9", 18)
    tax_calculation_obj = {
        "id": tax_calc_id,
        "object": "tax.calculation",
        "amount_total": grand_total_local,
        "currency": profile["currency"],
        "customer_details": {
            "address": {
                "country": profile["country"],
                "postal_code": postal_code,
            },
            "address_source": "shipping",
            "tax_ids": [{"type": "eu_vat", "value": vat_clean}] if vat_clean else [],
            "taxability_override": "reverse_charge" if is_eu_reverse_charge else "none",
        },
        "shipping_cost": {
            "amount": shipping_local,
            "amount_tax": shipping_tax_local,
            "tax_code": "txcd_92010001",
        },
        "tax_amount_exclusive": total_tax_local,
        "tax_amount_inclusive": 0,
        "tax_breakdown": [
            {
                "amount": total_tax_local,
                "inclusive": False,
                "tax_rate_details": {
                    "country": profile["country"],
                    "percentage_decimal": str(round(profile["tax_rate_physical"] * 100, 3)) if not is_eu_reverse_charge else "0.0",
                    "tax_type": "vat" if locale_code != "US" else "sales_tax",
                    "jurisdiction": profile["tax_jurisdiction"],
                },
                "taxability_reason": "reverse_charge" if is_eu_reverse_charge else "standard_rated",
                "taxable_amount": subtotal_local + shipping_local,
            }
        ],
        "line_items": line_items_detail,
    }

    fx_quote_obj = {
        "id": gen_stripe_id("fxq_1Q9", 18),
        "object": "fx_quote",
        "base_currency": "usd",
        "target_currency": profile["currency"],
        "exchange_rate": profile["fx_rate"],
        "fx_spread_bps": profile["fx_spread_bps"],
        "adaptive_pricing_enabled": True,
        "subscription_stability_buffer_pct": profile["stability_buffer_pct"] if has_subscription else 0.0,
        "lock_expires_at": int(time.time()) + 1800,
    }

    return {
        "locale": locale_code,
        "profile": profile,
        "subtotal_usd_cents": subtotal_usd_cents,
        "subtotal_local": subtotal_local,
        "shipping_local": shipping_local,
        "tax_local": total_tax_local,
        "total_local": grand_total_local,
        "formatted": {
            "subtotal": format_currency_amount(subtotal_local, locale_code),
            "shipping": "Free" if shipping_local == 0 else format_currency_amount(shipping_local, locale_code),
            "tax": format_currency_amount(total_tax_local, locale_code),
            "total": format_currency_amount(grand_total_local, locale_code),
        },
        "is_eu_reverse_charge": is_eu_reverse_charge,
        "has_subscription": has_subscription,
        "has_physical": has_physical,
        "connect_transfers": connect_transfers,
        "tax_calculation": tax_calculation_obj,
        "fx_quote": fx_quote_obj,
    }


def forward_to_live_stripe_if_configured(endpoint_path: str, form_params: dict[str, Any]) -> dict[str, Any] | None:
    """Calls https://api.stripe.com/v1/... when live_stripe_api mode and secret_key are configured."""
    sk = RUNTIME_CONFIG.get("secret_key", "").strip()
    if RUNTIME_CONFIG.get("mode") != "live_stripe_api" or not sk.startswith("sk_"):
        return None
    url = f"https://api.stripe.com{endpoint_path}"
    encoded_data = urllib.parse.urlencode(form_params).encode("utf-8")
    req = urllib.request.Request(url, data=encoded_data, method="POST")
    req.add_header("Authorization", f"Bearer {sk}")
    req.add_header("Stripe-Version", RUNTIME_CONFIG["api_version"])
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            return {"_stripe_http_error": e.code, "error": json.loads(err_body)}
        except json.JSONDecodeError:
            return {"_stripe_http_error": e.code, "error": {"message": err_body}}
    except Exception as exc:
        return {"_stripe_http_error": 502, "error": {"message": str(exc)}}


AGENTIC_ORDERS_STORE: dict[str, dict[str, Any]] = {}


def parse_agentic_natural_language_prompt(
    prompt: str,
    default_locale: str = "US",
    budget_override_usd: float | None = None,
    rail_override: str | None = None,
) -> dict[str, Any]:
    """Local NLU & Function-Calling Parser for the Stripe Agentic Commerce Chatbot."""
    text = (prompt or "").strip()
    lower = text.lower()

    # 1. Locale & Tax Jurisdiction Detection
    detected_locale = default_locale
    if any(k in lower for k in ("berlin", "germany", "munich", "frankfurt", "de8", "de1", "eurc", "mwst")):
        detected_locale = "DE"
    elif any(k in lower for k in ("amsterdam", "netherlands", "dutch", "ideal", "nl8")):
        detected_locale = "NL"
    elif any(k in lower for k in ("london", "uk", "britain", "gbp", "£", "clearpay")):
        detected_locale = "GB"
    elif any(k in lower for k in ("tokyo", "japan", "jpy", "¥", "paypay", "konbini")):
        detected_locale = "JP"
    elif any(k in lower for k in ("istanbul", "türkiye", "turkey", "try", "₺", "kdv")):
        detected_locale = "TR"
    elif any(k in lower for k in ("new york", "nyc", "united states", "usa")):
        detected_locale = "US"

    # 2. EU B2B VAT ID Detection (e.g., DE811907980, NL820194812B01)
    vat_match = re.search(r"\b([A-Z]{2}[0-9A-Z]{8,12})\b", text.upper())
    detected_vat_id = vat_match.group(1) if vat_match and vat_match.group(1)[:2] in ("DE", "NL", "FR", "IT", "ES", "AT", "BE", "SE") else ""
    if not detected_vat_id and ("reverse charge" in lower or "vat" in lower) and detected_locale in ("DE", "NL"):
        detected_vat_id = "DE811907980" if detected_locale == "DE" else "NL820194812B01"

    # 3. Payment Rail & Bridge Stablecoin Detection
    payment_method_type = "card"
    bridge_asset = "usdc"
    bridge_chain = "base"
    if rail_override and rail_override != "auto":
        if rail_override.startswith("crypto"):
            payment_method_type = "crypto_bridge"
            if "solana" in rail_override:
                bridge_chain = "solana"
            if "usdb" in rail_override:
                bridge_asset = "usdb"
            elif "eurc" in rail_override:
                bridge_asset = "eurc"
        else:
            payment_method_type = rail_override
    else:
        if any(k in lower for k in ("usdc", "usdb", "eurc", "stablecoin", "bridge", "crypto", "on-chain", "onchain", "solana", "base l2", "using base")):
            payment_method_type = "crypto_bridge"
            if "usdb" in lower:
                bridge_asset = "usdb"
            elif "eurc" in lower or detected_locale in ("DE", "NL"):
                bridge_asset = "eurc" if "eurc" in lower else "usdc"
            if "solana" in lower:
                bridge_chain = "solana"
            elif "stellar" in lower:
                bridge_chain = "stellar"
            elif "arbitrum" in lower:
                bridge_chain = "arbitrum"
            else:
                bridge_chain = "base"
        elif any(k in lower for k in ("link", "1-click", "one-click")):
            payment_method_type = "link"
        elif any(k in lower for k in ("sepa", "iban")):
            payment_method_type = "sepa_debit"

    # 4. Budget Guardrail Extraction (e.g., "under $1,400", "budget of $900", "max 1200", "limit $500")
    budget_usd = budget_override_usd
    if budget_usd is None or budget_usd <= 0:
        budget_patterns = [
            r"(?:under|below|max|maximum|budget(?:\s+of)?|limit(?:\s+of)?|up\s+to|within)\s*[\$€£]?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
            r"[\$€£]\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:budget|max|limit|ceiling)",
        ]
        for pat in budget_patterns:
            m = re.search(pat, lower)
            if m:
                try:
                    budget_usd = float(m.group(1).replace(",", ""))
                    break
                except ValueError:
                    pass
    if budget_usd is None or budget_usd <= 0:
        budget_usd = 2500.0
    budget_limit_usd_cents = int(round(budget_usd * 100))

    # 5. SKU & Quantity Extraction from Natural Language
    product_rules = [
        ("prod_synth_mk2", ["synth", "synthesizer", "mk-ii", "mk2", "workstation", "field synth"]),
        ("prod_monolith_console", ["monolith", "console", "fader", "controller", "summing", "mastering console", "tactile console"]),
        ("prod_planar_headphones", ["headphone", "headphones", "planar", "titanium", "earcup", "reference monitor", "monitors"]),
        ("prod_neural_cloud_pro", ["neural", "cloud", "stem", "subscription", "saas", "metronome", "suite", "dsp key", "recurring"]),
        ("prod_ambernex_dsp", ["ambernex", "euro-dsp", "reverb", "granular", "effects", "klangwerk", "dsp unit", "dsp module", "amber"]),
        ("prod_kyoto_mic", ["kyoto", "mic", "microphone", "binaural", "condenser", "brass", "field mic"]),
    ]

    word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
    selected_items: list[dict[str, Any]] = []

    for prod_id, keywords in product_rules:
        matched_kw = next((kw for kw in keywords if kw in lower), None)
        if matched_kw:
            qty = 1
            # Look for a number or quantity word right before the matched keyword
            qty_regex = rf"(?:(\d+|one|two|three|four|five)\s*x?\s+(?:\w+\s+){{0,2}}{re.escape(matched_kw)})"
            qm = re.search(qty_regex, lower)
            if qm:
                raw_q = qm.group(1)
                qty = int(raw_q) if raw_q.isdigit() else word_to_num.get(raw_q, 1)
            selected_items.append({"id": prod_id, "quantity": max(1, min(10, qty))})

    # High-level intent fallback if user didn't name specific SKUs
    intent_rationale_prefix = "Matched explicit product entities from your natural-language prompt"
    if not selected_items:
        if any(k in lower for k in ("cheapest", "starter", "entry", "lowest", "budget rig")):
            selected_items = [
                {"id": "prod_kyoto_mic", "quantity": 1},
                {"id": "prod_neural_cloud_pro", "quantity": 1},
            ]
            intent_rationale_prefix = "Assembled the most cost-effective entry studio bundle (Kyoto Binaural Mic + Neural Cloud Suite)"
        elif any(k in lower for k in ("all", "everything", "complete catalog", "every item")):
            selected_items = [{"id": p["id"], "quantity": 1} for p in CATALOG]
            intent_rationale_prefix = "Selected the complete 6-item Aetheria Labs flagship hardware & cloud catalog"
        elif any(k in lower for k in ("master", "mastering", "studio")):
            selected_items = [
                {"id": "prod_monolith_console", "quantity": 1},
                {"id": "prod_planar_headphones", "quantity": 1},
                {"id": "prod_neural_cloud_pro", "quantity": 1},
            ]
            intent_rationale_prefix = "Curated the Studio Mastering Suite (Monolith Console + Planar Headphones + Neural Cloud Pro)"
        elif any(k in lower for k in ("marketplace", "creator", "partner", "connect", "split")):
            selected_items = [
                {"id": "prod_ambernex_dsp", "quantity": 1},
                {"id": "prod_kyoto_mic", "quantity": 1},
            ]
            intent_rationale_prefix = "Curated the Multi-Vendor Creator Marketplace Bundle (Berlin AmberNex DSP + Kyoto Binaural Mic)"
        else:
            selected_items = [
                {"id": "prod_synth_mk2", "quantity": 1},
                {"id": "prod_kyoto_mic", "quantity": 1},
                {"id": "prod_neural_cloud_pro", "quantity": 1},
            ]
            intent_rationale_prefix = "Curated the Flagship Portable Field Synthesis & Binaural Recording Rig"

    return {
        "prompt": text,
        "detected_locale": detected_locale,
        "detected_vat_id": detected_vat_id,
        "payment_method_type": payment_method_type,
        "bridge_asset": bridge_asset,
        "bridge_chain": bridge_chain,
        "budget_limit_usd_cents": budget_limit_usd_cents,
        "selected_items": selected_items,
        "intent_rationale_prefix": intent_rationale_prefix,
    }


def try_local_ollama_reasoning(
    prompt: str,
    parsed_summary: str,
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
    ollama_model: str = "llama3.2",
) -> tuple[str | None, str]:
    """Optionally queries a local Ollama daemon if running; falls back cleanly in <150ms if offline."""
    payload = json.dumps({
        "model": ollama_model,
        "prompt": (
            "You are the Aetheria Labs Local Agentic Commerce Assistant powered by Stripe Agentic Commerce Protocol. "
            f"The user asked: '{prompt}'. "
            f"You executed Stripe MCP tools with result: {parsed_summary}. "
            "Write a concise, helpful 2-sentence confirmation explaining the items selected, the single-use spt_agent_ token guardrail, and payment settlement."
        ),
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(ollama_url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            reply_text = body.get("response", "").strip()
            if reply_text:
                return reply_text, f"Ollama Local LLM ({ollama_model} @ 127.0.0.1:11434) + Stripe MCP Tool Executor"
    except Exception:
        pass
    return None, "Built-in Local Agentic LLM Engine v2.6 (Deterministic NLU + Stripe MCP Function-Calling)"


def execute_agentic_commerce_chat(body: dict[str, Any]) -> dict[str, Any]:
    """Executes the 6-Step Stripe Agentic Commerce Protocol (ACP) pipeline for the Local LLM Chatbot."""
    prompt = str(body.get("message") or "Buy me the Field Synthesizer MK-II and Kyoto Binaural Mic under $1,400 using USDC on Base")
    default_locale = str(body.get("locale") or "US")
    execution_mode = str(body.get("execution_mode") or "auto_complete")  # "auto_complete" or "human_in_the_loop"
    budget_override = body.get("budget_override_usd")
    rail_override = body.get("payment_rail_override")
    use_ollama = bool(body.get("try_ollama", False))

    parsed = parse_agentic_natural_language_prompt(
        prompt=prompt,
        default_locale=default_locale,
        budget_override_usd=float(budget_override) if budget_override else None,
        rail_override=str(rail_override) if rail_override else None,
    )

    locale_code = parsed["detected_locale"]
    vat_id = parsed["detected_vat_id"]
    selected_items = parsed["selected_items"]
    budget_limit_usd_cents = parsed["budget_limit_usd_cents"]
    payment_method_type = parsed["payment_method_type"]
    bridge_asset = parsed["bridge_asset"]
    bridge_chain = parsed["bridge_chain"]
    now_ts = int(time.time())

    # -------------------------------------------------------------------------
    # STEP 1: Intent Parsing & Zero-Trust Server-Side Catalog SKU Resolution
    # -------------------------------------------------------------------------
    resolved_skus = []
    for item in selected_items:
        prod = CATALOG_BY_ID.get(item["id"])
        if prod:
            resolved_skus.append({
                "sku_id": prod["id"],
                "price_id": prod["price_id"],
                "name": prod["name"],
                "quantity": item["quantity"],
                "canonical_unit_amount_usd_cents": prod["unit_amount_usd"],
                "line_subtotal_usd_cents": prod["unit_amount_usd"] * item["quantity"],
                "commerce_model": prod["commerce_model"],
                "tax_code": prod["tax_code"],
                "connect_seller": prod["seller"]["name"] if prod.get("seller") else None,
            })

    step1_req = {
        "natural_language_prompt": prompt,
        "client_amount_accepted": False,
        "extracted_entities": {
            "skus_requested": selected_items,
            "target_locale": locale_code,
            "b2b_vat_id": vat_id or None,
            "preferred_payment_rail": payment_method_type,
            "bridge_network": bridge_chain if payment_method_type == "crypto_bridge" else None,
            "budget_ceiling_usd_cents": budget_limit_usd_cents,
        },
    }
    step1_resp = {
        "tool": "mcp://stripe.agentic/catalog.resolve_skus",
        "zero_trust_verified": True,
        "resolved_line_items": resolved_skus,
        "rationale": parsed["intent_rationale_prefix"],
    }

    # -------------------------------------------------------------------------
    # STEP 2: Stripe Tax API (/v1/tax/calculations) & Adaptive Pricing Quote
    # -------------------------------------------------------------------------
    default_postals = {"US": "10001", "DE": "10115", "NL": "1012 JS", "GB": "EC2A 4NE", "TR": "34394", "JP": "150-0001"}
    postal_code = default_postals.get(locale_code, "10001")
    calc = calculate_cart_pricing_and_tax(selected_items, locale_code, vat_id, postal_code, True)
    tax_obj = calc["tax_calculation"]

    step2_curl = (
        f"curl https://api.stripe.com/v1/tax/calculations \\\n"
        f"  -u sk_test_...: \\\n"
        f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
        f"  -d currency={tax_obj['currency']} \\\n"
        f"  -d 'customer_details[address][country]={calc['profile']['country']}' \\\n"
        f"  -d 'customer_details[address][postal_code]={postal_code}'"
        + (f" \\\n  -d 'customer_details[tax_ids][0][type]=eu_vat' -d 'customer_details[tax_ids][0][value]={vat_id}'" if vat_id else "")
    )
    record_api_log("POST", "/v1/tax/calculations [AGENTIC STEP 2]", {"items": selected_items, "locale": locale_code, "vat_id": vat_id}, tax_obj, 200, 54, step2_curl)

    # -------------------------------------------------------------------------
    # STEP 3: Agentic OrderIntent & Cryptographic Spend Mandate (/v1/agentic/order_intents)
    # -------------------------------------------------------------------------
    order_intent_id = gen_stripe_id("aoi_1Q9", 18)
    order_id = f"ord_agent_{gen_stripe_id('llm', 8)}"
    within_budget = calc["subtotal_usd_cents"] <= budget_limit_usd_cents
    mandate_hash = hashlib.sha256(f"{order_intent_id}:{order_id}:{calc['total_local']}:{budget_limit_usd_cents}".encode("utf-8")).hexdigest()[:32]

    order_intent_status = (
        "blocked_by_budget_guardrail"
        if not within_budget
        else ("requires_human_confirmation" if execution_mode == "human_in_the_loop" else "approved_for_execution")
    )

    step3_req = {
        "agent_id": "agt_aetheria_local_llm_v2",
        "order_id": order_id,
        "spending_controls": {
            "budget_ceiling_usd_cents": budget_limit_usd_cents,
            "cart_subtotal_usd_cents": calc["subtotal_usd_cents"],
            "presentment_total_minor": calc["total_local"],
            "currency": calc["profile"]["currency"],
        },
        "tax_calculation": tax_obj["id"],
    }
    step3_resp = {
        "id": order_intent_id,
        "object": "agentic.order_intent",
        "agent_id": "agt_aetheria_local_llm_v2",
        "order_id": order_id,
        "status": order_intent_status,
        "within_budget": within_budget,
        "budget_ceiling_usd_cents": budget_limit_usd_cents,
        "cart_subtotal_usd_cents": calc["subtotal_usd_cents"],
        "presentment_total_minor": calc["total_local"],
        "presentment_formatted": calc["formatted"]["total"],
        "cryptographic_mandate_hash": mandate_hash,
    }
    step3_curl = (
        f"curl https://api.stripe.com/v1/agentic/order_intents \\\n"
        f"  -u sk_test_...: \\\n"
        f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
        f"  -d agent_id=agt_aetheria_local_llm_v2 \\\n"
        f"  -d 'metadata[order_id]={order_id}' \\\n"
        f"  -d 'spending_controls[max_amount]={calc['total_local']}' \\\n"
        f"  -d 'spending_controls[currency]={calc['profile']['currency']}'"
    )
    record_api_log("POST", "/v1/agentic/order_intents [AGENTIC STEP 3]", step3_req, step3_resp, 200 if within_budget else 400, 68, step3_curl)
    emit_webhook_event("agentic.order_intent.created", step3_resp)

    steps_trace: list[dict[str, Any]] = [
        {
            "step_number": 1,
            "step_id": "intent_and_zero_trust_catalog",
            "title": "1. Natural-Language Intent Parsing & Zero-Trust SKU Resolution",
            "stripe_primitive": "Stripe Agentic MCP Catalog Resolver (Zero-Trust Minor Units)",
            "endpoint": "mcp://stripe.agentic/catalog.resolve_skus",
            "status": "completed",
            "latency_ms": 18,
            "explanation": (
                f"Parsed your prompt into {len(resolved_skus)} canonical SKU(s) ({', '.join(r['sku_id'] + ' ×' + str(r['quantity']) for r in resolved_skus)}). "
                "Enforced Best Practice #1 (Zero Trust on Client-Side Amounts): the LLM never passes prices; integer minor units are resolved strictly from the server-side CATALOG."
            ),
            "curl_snippet": "# Internal MCP Tool Call — Server-Side Catalog Lookup Only (Zero Client Price Trust)",
            "request_payload": step1_req,
            "response_payload": step1_resp,
        },
        {
            "step_number": 2,
            "step_id": "adaptive_pricing_and_stripe_tax",
            "title": "2. Adaptive Pricing FX Quote, Stripe Tax & Connect Split Calculation",
            "stripe_primitive": "Stripe Tax API + Adaptive Pricing FX Quotes + Connect v2 Splits",
            "endpoint": "POST /v1/tax/calculations",
            "status": "completed",
            "latency_ms": 54,
            "explanation": (
                f"Calculated local presentment in {calc['profile']['currency'].upper()} ({calc['formatted']['total']} total = {calc['formatted']['subtotal']} subtotal + "
                f"{calc['formatted']['tax']} {calc['profile']['tax_name']}{' [0% EU B2B Reverse Charge]' if calc['is_eu_reverse_charge'] else ''}). "
                f"Prepared {len(calc['connect_transfers'])} automated Connect v2 partner split payout(s)."
            ),
            "curl_snippet": step2_curl,
            "request_payload": {"items": selected_items, "locale": locale_code, "vat_id": vat_id or None},
            "response_payload": {
                "tax_calculation_id": tax_obj["id"],
                "fx_quote_id": calc["fx_quote"]["id"],
                "exchange_rate": calc["fx_quote"]["exchange_rate"],
                "formatted_breakdown": calc["formatted"],
                "is_eu_reverse_charge": calc["is_eu_reverse_charge"],
                "connect_transfers": calc["connect_transfers"],
            },
        },
        {
            "step_number": 3,
            "step_id": "agentic_order_intent_guardrail",
            "title": "3. Agentic OrderIntent & Spend Mandate Verification",
            "stripe_primitive": "Stripe Agentic Commerce Toolkit (/v1/agentic/order_intents)",
            "endpoint": "POST /v1/agentic/order_intents",
            "status": "completed" if within_budget else "blocked_by_guardrail",
            "latency_ms": 68,
            "explanation": (
                f"Verified cart subtotal (${calc['subtotal_usd_cents'] / 100:,.2f} USD) against your mandate ceiling (${budget_limit_usd_cents / 100:,.2f} USD) -> "
                + (
                    f"PASSED! Issued OrderIntent {order_intent_id} with SHA-256 mandate hash {mandate_hash[:16]}..."
                    if within_budget
                    else f"BLOCKED! Cart subtotal (${calc['subtotal_usd_cents'] / 100:,.2f}) exceeds your ${budget_limit_usd_cents / 100:,.2f} budget guardrail. Execution halted safely before token minting."
                )
            ),
            "curl_snippet": step3_curl,
            "request_payload": step3_req,
            "response_payload": step3_resp,
        },
    ]

    # If budget guardrail blocked the order, halt Steps 4, 5, 6 and return immediately
    if not within_budget:
        for skipped_num, skipped_title, skipped_ep in [
            (4, "4. Single-Use Delegated Payment Token (spt_agent_...)", "POST /v1/agentic/delegated_payment_tokens"),
            (5, "5. Deterministic Idempotent PaymentIntent Execution", "POST /v1/payment_intents"),
            (6, "6. Cryptographic Webhook Emission & Order Fulfillment", "Stripe-Signature Webhook Dispatch"),
        ]:
            steps_trace.append({
                "step_number": skipped_num,
                "step_id": f"skipped_step_{skipped_num}",
                "title": skipped_title,
                "stripe_primitive": "Halted by Step 3 Spend Guardrail",
                "endpoint": skipped_ep,
                "status": "skipped",
                "latency_ms": 0,
                "explanation": "Skipped because Step 3 Spend Guardrail blocked the cart for exceeding the user's budget mandate.",
                "curl_snippet": "# Not executed — blocked by budget guardrail",
                "request_payload": {},
                "response_payload": {"status": "halted_by_budget_guardrail"},
            })

        assistant_reply = (
            f"I parsed your request for **{', '.join(r['name'] + ' (×' + str(r['quantity']) + ')' for r in resolved_skus)}**, "
            f"which totals **${calc['subtotal_usd_cents'] / 100:,.2f} USD** ({calc['formatted']['total']} with tax). "
            f"However, your spending guardrail is set to **${budget_limit_usd_cents / 100:,.2f} USD**, so **Step 3 (`POST /v1/agentic/order_intents`)** "
            f"automatically blocked the transaction (`status: blocked_by_budget_guardrail`) before any payment token could be minted. "
            "Try increasing your budget ceiling or asking for a lower-cost bundle!"
        )
        return {
            "status": "blocked_by_budget_guardrail",
            "llm_engine": "Built-in Local Agentic LLM Engine v2.6 (Deterministic NLU + Stripe MCP Function-Calling)",
            "assistant_message": assistant_reply,
            "parsed_intent": parsed,
            "order_intent": step3_resp,
            "delegated_payment_token": None,
            "payment_intent": None,
            "calculation": calc,
            "steps": steps_trace,
        }

    # -------------------------------------------------------------------------
    # STEP 4: Single-Use Scoped Delegated Payment Token (spt_agent_...)
    # -------------------------------------------------------------------------
    spt_id = gen_stripe_id("spt_agent_1Q9", 20)
    dpt_obj = {
        "id": spt_id,
        "object": "agentic.delegated_payment_token",
        "order_intent": order_intent_id,
        "network": "bridge_stablecoin_paymaster" if payment_method_type == "crypto_bridge" else "visa_agentic_token_service",
        "rail": f"Bridge {bridge_asset.upper()} on {bridge_chain.upper()}" if payment_method_type == "crypto_bridge" else payment_method_type.upper(),
        "max_amount": calc["total_local"],
        "currency": calc["profile"]["currency"],
        "allowed_mcc": ["5733", "5734"],
        "merchant_lock": "acct_1Q9AetheriaLabsFlagship",
        "single_use": True,
        "expires_at": now_ts + 600,
        "ttl_seconds": 600,
        "cryptographic_mandate_hash": mandate_hash,
        "pan_exposed_to_llm": False,
    }
    step4_curl = (
        f"curl https://api.stripe.com/v1/agentic/delegated_payment_tokens \\\n"
        f"  -u sk_test_...: \\\n"
        f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
        f"  -d order_intent={order_intent_id} \\\n"
        f"  -d 'spending_controls[max_amount]={calc['total_local']}' \\\n"
        f"  -d 'spending_controls[currency]={calc['profile']['currency']}' \\\n"
        f"  -d 'spending_controls[allowed_mcc][]=5733' -d 'spending_controls[allowed_mcc][]=5734' \\\n"
        f"  -d single_use=true -d ttl_seconds=600"
    )
    record_api_log("POST", "/v1/agentic/delegated_payment_tokens [AGENTIC STEP 4]", {"order_intent": order_intent_id, "max_amount": calc["total_local"]}, dpt_obj, 200, 49, step4_curl)

    steps_trace.append({
        "step_number": 4,
        "step_id": "delegated_payment_token_mint",
        "title": "4. Single-Use Scoped Delegated Payment Token (spt_agent_...)",
        "stripe_primitive": "Visa Agentic Token Service / Stripe Shared Payment Token",
        "endpoint": "POST /v1/agentic/delegated_payment_tokens",
        "status": "completed",
        "latency_ms": 49,
        "explanation": (
            f"Provisioned single-use credential `{spt_id}` via {dpt_obj['network']}. "
            f"Cryptographically locked to MCC 5733/5734, hard-capped at `{calc['total_local']}` minor units ({calc['formatted']['total']}), "
            "and valid for 600 seconds. The LLM agent never sees raw card numbers or private keys."
        ),
        "curl_snippet": step4_curl,
        "request_payload": {"order_intent": order_intent_id, "max_amount": calc["total_local"], "allowed_mcc": ["5733", "5734"], "single_use": True},
        "response_payload": dpt_obj,
    })

    # Save pending or active order in AGENTIC_ORDERS_STORE so human_in_the_loop mode can confirm it later
    idem_key = f"pi_create_{order_id}_attempt_1"
    AGENTIC_ORDERS_STORE[order_intent_id] = {
        "order_intent_id": order_intent_id,
        "order_id": order_id,
        "idempotency_key": idem_key,
        "selected_items": selected_items,
        "resolved_skus": resolved_skus,
        "locale_code": locale_code,
        "vat_id": vat_id,
        "postal_code": postal_code,
        "payment_method_type": payment_method_type,
        "bridge_asset": bridge_asset,
        "bridge_chain": bridge_chain,
        "delegated_payment_token": dpt_obj,
        "calculation": calc,
        "order_intent": step3_resp,
        "status": order_intent_status,
    }

    # If in human_in_the_loop mode, pause at Step 5 for explicit user confirmation
    if execution_mode == "human_in_the_loop":
        steps_trace.append({
            "step_number": 5,
            "step_id": "payment_intent_awaiting_human",
            "title": "5. PaymentIntent Execution (Paused for Human-in-the-Loop Confirmation)",
            "stripe_primitive": "PaymentIntent API (/v1/payment_intents + Deterministic Idempotency-Key)",
            "endpoint": "POST /v1/payment_intents [AWAITING APPROVAL]",
            "status": "awaiting_human_approval",
            "latency_ms": 0,
            "explanation": (
                f"Paused in `requires_human_confirmation` mode. Ready to execute `POST /v1/payment_intents` with "
                f"`Idempotency-Key: {idem_key}`, `payment_method={spt_id}`, and `expand=['latest_charge.balance_transaction']`. "
                "Click 'Approve & Execute PaymentIntent' to complete settlement."
            ),
            "curl_snippet": (
                f"curl https://api.stripe.com/v1/payment_intents \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -H 'Idempotency-Key: {idem_key}' \\\n"
                f"  -d amount={calc['total_local']} -d currency={calc['profile']['currency']} \\\n"
                f"  -d payment_method={spt_id} -d confirm=true \\\n"
                f"  -d 'expand[]=latest_charge.balance_transaction'"
            ),
            "request_payload": {"idempotency_key": idem_key, "payment_method": spt_id, "amount_minor": calc["total_local"]},
            "response_payload": {"status": "requires_human_confirmation", "order_intent_id": order_intent_id},
        })
        steps_trace.append({
            "step_number": 6,
            "step_id": "webhooks_awaiting_human",
            "title": "6. Signed Webhook Emission & Fulfillment (Pending Step 5 Approval)",
            "stripe_primitive": "Stripe Webhooks (HMAC-SHA256 Stripe-Signature)",
            "endpoint": "POST /api/stripe/webhooks/receive",
            "status": "awaiting_human_approval",
            "latency_ms": 0,
            "explanation": "Emitted `agentic.order_intent.created`. Final `payment_intent.succeeded` and `transfer.created` webhooks will fire immediately upon your confirmation.",
            "curl_snippet": "# Waiting for human confirmation of OrderIntent " + order_intent_id,
            "request_payload": {},
            "response_payload": {"emitted_so_far": ["agentic.order_intent.created"]},
        })

        assistant_reply = (
            f"I've prepared your **Agentic OrderIntent (`{order_intent_id}`)** for **{', '.join(r['name'] + ' ×' + str(r['quantity']) for r in resolved_skus)}** "
            f"at **{calc['formatted']['total']}** ({calc['profile']['tax_name']}{' — 0% Reverse Charge applied' if calc['is_eu_reverse_charge'] else ''}). "
            f"Stripe minted single-use Delegated Payment Token **`{spt_id}`** ({dpt_obj['rail']}) capped at `{calc['total_local']}` minor units. "
            f"Because **Human-in-the-Loop Confirmation** is enabled, click **Approve & Settle OrderIntent** below to execute `POST /v1/payment_intents` with `Idempotency-Key: {idem_key}`."
        )
        return {
            "status": "requires_human_confirmation",
            "llm_engine": "Built-in Local Agentic LLM Engine v2.6 (Human-in-the-Loop Gate Active)",
            "assistant_message": assistant_reply,
            "parsed_intent": parsed,
            "order_intent": step3_resp,
            "delegated_payment_token": dpt_obj,
            "payment_intent": None,
            "calculation": calc,
            "steps": steps_trace,
        }

    # -------------------------------------------------------------------------
    # STEP 5 & STEP 6: Auto-Complete Execution via confirm_agentic_order_intent
    # -------------------------------------------------------------------------
    settlement = confirm_agentic_order_intent(order_intent_id, use_ollama=use_ollama, original_prompt=prompt)
    steps_trace.extend(settlement["steps_5_and_6"])

    return {
        "status": "succeeded",
        "llm_engine": settlement["llm_engine"],
        "assistant_message": settlement["assistant_message"],
        "parsed_intent": parsed,
        "order_intent": settlement["order_intent"],
        "delegated_payment_token": dpt_obj,
        "payment_intent": settlement["payment_intent"],
        "calculation": calc,
        "steps": steps_trace,
    }


def confirm_agentic_order_intent(
    order_intent_id: str,
    use_ollama: bool = False,
    original_prompt: str = "",
) -> dict[str, Any]:
    """Executes Steps 5 & 6 for a prepared Agentic OrderIntent (used by both auto_complete and human confirmation)."""
    stored = AGENTIC_ORDERS_STORE.get(order_intent_id)
    if not stored:
        raise KeyError(f"Agentic OrderIntent {order_intent_id} not found")

    calc = stored["calculation"]
    dpt_obj = stored["delegated_payment_token"]
    order_id = stored["order_id"]
    idem_key = stored["idempotency_key"]
    payment_method_type = stored["payment_method_type"]
    bridge_asset = stored["bridge_asset"]
    bridge_chain = stored["bridge_chain"]
    resolved_skus = stored["resolved_skus"]
    now_ts = int(time.time())

    pi_id = gen_stripe_id("pi_3Q9Agent", 17)
    charge_id = gen_stripe_id("ch_3Q9Agent", 17)
    txn_id = gen_stripe_id("txn_3Q9Agent", 17)
    transfer_group = f"ORDER_{gen_stripe_id('AGNT', 8)}"
    req_id = gen_stripe_id("req", 14)

    structured_metadata = {
        "order_id": order_id,
        "agent_id": "agt_aetheria_local_llm_v2",
        "agentic_order_intent": order_intent_id,
        "delegated_payment_token": dpt_obj["id"],
        "customer_tier": "enterprise",
        "erp_cost_center": "IT-01",
    }

    is_bridge_crypto = payment_method_type == "crypto_bridge"
    bridge_details = None
    if is_bridge_crypto:
        usd_equiv = (calc["total_local"] / calc["profile"]["fx_rate"]) if not calc["profile"]["zero_decimal"] else (calc["total_local"] / calc["profile"]["fx_rate"]) * 100
        stable_units = round(usd_equiv / 100.0, 2) if bridge_asset != "eurc" else round((usd_equiv * 0.92) / 100.0, 2)
        dep_addr = (
            f"Brdg{gen_stripe_id('Sol', 28).replace('_', '')}"
            if bridge_chain == "solana"
            else f"0x8F4e{hashlib.sha256(pi_id.encode()).hexdigest()[:36]}"
        )
        bridge_details = {
            "orchestrator": "Bridge (a Stripe company) — v0 Orchestration API",
            "bridge_transfer_id": gen_stripe_id("br_tr_1Q9", 16),
            "liquidation_address_id": gen_stripe_id("br_liq_1Q9", 16),
            "onchain_deposit_address": dep_addr,
            "source_asset": bridge_asset.upper(),
            "source_chain": bridge_chain,
            "stablecoin_amount_paid": f"{stable_units:.2f} {bridge_asset.upper()}",
            "destination_currency": calc["profile"]["currency"].upper(),
            "paymaster_gas_sponsored": True,
            "tx_hash": f"0x{hashlib.sha256(f'{pi_id}:{bridge_chain}'.encode()).hexdigest()[:48]}",
            "finality_ms": 420 if bridge_chain == "solana" else 1480,
        }

    gross_amt = calc["total_local"]
    stripe_fee_amt = int(round(gross_amt * (0.005 if is_bridge_crypto else 0.029) + (0 if calc["profile"]["zero_decimal"] else 30)))
    total_app_fee = sum(t["application_fee_amount"] for t in calc["connect_transfers"])

    expanded_charge = {
        "id": charge_id,
        "object": "charge",
        "amount": gross_amt,
        "currency": calc["profile"]["currency"],
        "paid": True,
        "status": "succeeded",
        "payment_method": dpt_obj["id"],
        "metadata": structured_metadata,
        "balance_transaction": {
            "id": txn_id,
            "object": "balance_transaction",
            "amount": gross_amt,
            "fee": stripe_fee_amt,
            "net": max(0, gross_amt - stripe_fee_amt),
            "currency": calc["profile"]["currency"],
            "exchange_rate": calc["fx_quote"]["exchange_rate"],
            "type": "charge",
        },
    }

    pi_object = {
        "id": pi_id,
        "object": "payment_intent",
        "amount": gross_amt,
        "amount_capturable": 0,
        "amount_received": gross_amt,
        "currency": calc["profile"]["currency"],
        "status": "succeeded",
        "capture_method": "automatic",
        "created": now_ts,
        "customer": "cus_Q9AetheriaDemoStudio",
        "payment_method": dpt_obj["id"],
        "payment_method_types": ["crypto" if is_bridge_crypto else payment_method_type],
        "metadata": structured_metadata,
        "latest_charge": expanded_charge,
        "latest_charge_id": charge_id,
        "agentic_commerce": {
            "order_intent_id": order_intent_id,
            "delegated_payment_token": dpt_obj["id"],
            "single_use_token_consumed": True,
            "cryptographic_mandate_hash": dpt_obj["cryptographic_mandate_hash"],
        },
        "zero_trust_pricing_audit": {
            "client_amount_accepted": False,
            "server_catalog_lookup": True,
            "integer_minor_units": gross_amt,
            "canonical_skus_resolved": [
                {"sku_id": r["sku_id"], "qty": r["quantity"], "unit_minor": r["canonical_unit_amount_usd_cents"]}
                for r in resolved_skus
            ],
        },
        "idempotency_protection": {
            "idempotency_key": idem_key,
            "order_id": order_id,
            "attempt_no": 1,
            "ttl_hours": 24,
        },
        "bridge_stablecoin_details": bridge_details,
        "radar_evaluation": {
            "risk_score": 2 if is_bridge_crypto else 4,
            "risk_level": "normal",
            "matched_rule": "pass_agentic_spt_cryptographic_mandate_verified",
            "network_token_cryptogram": "eip712_permit2_verified" if is_bridge_crypto else "spt_vts_cryptogram_eci05",
        },
        "transfer_group": transfer_group if calc["connect_transfers"] else None,
        "application_fee_amount": total_app_fee if total_app_fee > 0 else None,
        "connect_transfers": calc["connect_transfers"],
    }

    PAYMENT_INTENTS_STORE[pi_id] = pi_object
    stored["status"] = "succeeded"
    stored["order_intent"]["status"] = "succeeded"
    stored["payment_intent"] = pi_object

    IDEMPOTENCY_STORE[idem_key] = {
        "created_at": now_ts,
        "param_hash": dpt_obj["cryptographic_mandate_hash"][:24],
        "order_id": order_id,
        "attempt_no": 1,
        "payment_intent_id": pi_id,
        "request_id": req_id,
        "status_code": 200,
        "response_payload": {"payment_intent": pi_object, "calculation": calc},
    }

    step5_curl = (
        f"curl https://api.stripe.com/v1/payment_intents \\\n"
        f"  -u sk_test_...: \\\n"
        f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
        f"  -H 'Idempotency-Key: {idem_key}' \\\n"
        f"  -d amount={gross_amt} \\\n"
        f"  -d currency={calc['profile']['currency']} \\\n"
        f"  -d payment_method={dpt_obj['id']} \\\n"
        f"  -d confirm=true \\\n"
        f"  -d 'expand[]=latest_charge.balance_transaction' \\\n"
        f"  -d 'metadata[order_id]={order_id}' \\\n"
        f"  -d 'metadata[agent_id]=agt_aetheria_local_llm_v2' \\\n"
        f"  -d 'metadata[customer_tier]=enterprise' \\\n"
        f"  -d 'metadata[erp_cost_center]=IT-01'"
    )
    record_api_log(
        "POST",
        "/v1/payment_intents [AGENTIC STEP 5]",
        {"idempotency_key": idem_key, "payment_method": dpt_obj["id"], "amount": gross_amt, "expand": ["latest_charge.balance_transaction"], "metadata": structured_metadata},
        pi_object,
        200,
        118,
        step5_curl,
    )

    emitted_webhooks = ["agentic.order_intent.created"]
    emit_webhook_event("payment_intent.created", pi_object, request_id=req_id)
    emitted_webhooks.append("payment_intent.created")
    if is_bridge_crypto and bridge_details:
        emit_webhook_event("bridge.liquidation_address.deposit_detected", bridge_details, request_id=req_id)
        emit_webhook_event("bridge.transfer.completed", bridge_details, request_id=req_id)
        emitted_webhooks.extend(["bridge.liquidation_address.deposit_detected", "bridge.transfer.completed"])
    emit_webhook_event("payment_intent.succeeded", pi_object, request_id=req_id)
    emitted_webhooks.append("payment_intent.succeeded")
    for tr in calc["connect_transfers"]:
        emit_webhook_event(
            "transfer.created",
            {
                "id": gen_stripe_id("tr_3Q9", 18),
                "object": "transfer",
                "amount": tr["net_transfer_amount"],
                "currency": tr["currency"],
                "destination": tr["destination_account"],
                "transfer_group": transfer_group,
                "source_transaction": pi_id,
                "metadata": structured_metadata,
            },
            request_id=req_id,
        )
        emitted_webhooks.append(f"transfer.created ({tr['destination_account']})")

    steps_5_and_6 = [
        {
            "step_number": 5,
            "step_id": "idempotent_payment_intent_execution",
            "title": "5. Deterministic Idempotent PaymentIntent Execution & Settlement",
            "stripe_primitive": "PaymentIntent API + Single-Call expand[] + Structured Metadata",
            "endpoint": "POST /v1/payment_intents",
            "status": "completed",
            "latency_ms": 118,
            "explanation": (
                f"Executed `POST /v1/payment_intents` with deterministic `Idempotency-Key: {idem_key}`, consuming single-use token `{dpt_obj['id']}`. "
                f"Hydrated `latest_charge.balance_transaction` (`{txn_id}`, Net: {format_currency_amount(expanded_charge['balance_transaction']['net'], stored['locale_code'])}) in 1 HTTP call (Best Practice #6) "
                f"and propagated `metadata.order_id={order_id}` (Best Practice #7)."
                + (f" Settled `{bridge_details['stablecoin_amount_paid']}` on `{bridge_chain.upper()}` via Bridge Liquidation Address `{bridge_details['liquidation_address_id']}`." if bridge_details else "")
            ),
            "curl_snippet": step5_curl,
            "request_payload": {
                "idempotency_key": idem_key,
                "amount": gross_amt,
                "currency": calc["profile"]["currency"],
                "payment_method": dpt_obj["id"],
                "expand": ["latest_charge.balance_transaction"],
                "metadata": structured_metadata,
            },
            "response_payload": pi_object,
        },
        {
            "step_number": 6,
            "step_id": "webhook_dispatch_and_fulfillment",
            "title": "6. Signed Webhook Emission (HMAC-SHA256) & Async Fulfillment",
            "stripe_primitive": "Stripe Webhooks (raw_body HMAC-SHA256 + Idempotent Event Queue)",
            "endpoint": "POST /api/stripe/webhooks/receive",
            "status": "completed",
            "latency_ms": 14,
            "explanation": (
                f"Dispatched {len(emitted_webhooks)} cryptographically signed webhook events ({', '.join(emitted_webhooks)}) with `Stripe-Signature` HMAC-SHA256 headers. "
                "Synced purchased items into the store ledger and Developer Workbench stream."
            ),
            "curl_snippet": (
                "# Signed Webhook Verification on Merchant Backend:\n"
                "event = stripe.Webhook.construct_event(payload=raw_body, sig_header=request.headers['Stripe-Signature'], secret=whsec_...)"
            ),
            "request_payload": {"emitted_events": emitted_webhooks, "order_id": order_id},
            "response_payload": {
                "webhook_delivery_status": "verified_200_ok",
                "events_emitted": emitted_webhooks,
                "payment_intent_id": pi_id,
                "balance_transaction_id": txn_id,
            },
        },
    ]

    summary_for_llm = (
        f"Items: {', '.join(r['name'] + ' x' + str(r['quantity']) for r in resolved_skus)}; "
        f"Total: {calc['formatted']['total']}; Token: {dpt_obj['id']}; PaymentIntent: {pi_id} (succeeded); "
        f"Idempotency-Key: {idem_key}; Rail: {dpt_obj['rail']}."
    )
    ollama_reply, engine_label = (
        try_local_ollama_reasoning(original_prompt or order_intent_id, summary_for_llm)
        if use_ollama
        else (None, "Built-in Local Agentic LLM Engine v2.6 (Deterministic NLU + Stripe MCP Function-Calling)")
    )

    assistant_reply = ollama_reply or (
        f"Purchase completed! I resolved **{', '.join(r['name'] + ' (×' + str(r['quantity']) + ')' for r in resolved_skus)}** from the server-side catalog, "
        f"verified your budget guardrail via **OrderIntent `{order_intent_id}`**, and minted single-use **Delegated Payment Token `{dpt_obj['id']}`** ({dpt_obj['rail']}). "
        f"**PaymentIntent `{pi_id}`** settled **{calc['formatted']['total']}** (`status: succeeded`) using deterministic `Idempotency-Key: {idem_key}` "
        f"with single-call `expand=['latest_charge.balance_transaction']` (`{txn_id}`)."
    )

    return {
        "llm_engine": engine_label,
        "assistant_message": assistant_reply,
        "order_intent": stored["order_intent"],
        "payment_intent": pi_object,
        "steps_5_and_6": steps_5_and_6,
    }


class StripeDemoHandler(http.server.SimpleHTTPRequestHandler):
    """Serves static frontend assets and handles all /api/... Stripe integration endpoints."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep server stdout clean
        pass

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            self._last_raw_body = b""
            return {}
        raw_bytes = self.rfile.read(length)
        self._last_raw_body = raw_bytes
        raw = raw_bytes.decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _resolve_request_path_and_query(self) -> tuple[str, dict[str, list[str]]]:
        parsed = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed.query)
        path = parsed.path
        if "__route" in query_params and query_params["__route"]:
            raw_route = query_params["__route"][0]
            if not raw_route.startswith("/"):
                raw_route = "/" + raw_route
            path = raw_route
        elif path in ("/api/index.py", "/api/index"):
            hdr_path = (
                self.headers.get("x-matched-path")
                or self.headers.get("x-invoke-path")
                or "/"
            )
            path = urllib.parse.urlparse(hdr_path).path or "/"
        return path, query_params

    def _serve_static_asset(self, path: str) -> None:
        rel_path = path.lstrip("/")
        if not rel_path or rel_path == "index.html":
            rel_path = "index.html"
        elif rel_path.startswith("static/"):
            rel_path = rel_path[len("static/") :]

        norm_rel = os.path.normpath(rel_path)
        if norm_rel.startswith("..") or os.path.isabs(norm_rel):
            self.send_error(403, "Forbidden")
            return

        candidate = os.path.join(STATIC_DIR, norm_rel)
        if not os.path.isfile(candidate):
            self.send_error(404, f"File not found: {path}")
            return

        ext = os.path.splitext(candidate)[1].lower()
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        ctype = content_types.get(ext, "application/octet-stream")
        with open(candidate, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if ext in (".jpg", ".jpeg", ".png", ".svg"):
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path, query_params = self._resolve_request_path_and_query()

        if path == "/api/state":
            self._send_json({
                "config": {
                    "mode": RUNTIME_CONFIG["mode"],
                    "publishable_key": RUNTIME_CONFIG["publishable_key"],
                    "has_secret_key": bool(RUNTIME_CONFIG.get("secret_key")),
                    "api_version": RUNTIME_CONFIG["api_version"],
                    "webhook_secret": RUNTIME_CONFIG["webhook_secret"],
                },
                "catalog": CATALOG,
                "locales": LOCALE_PROFILES,
                "meter_usage": METER_USAGE_STATE,
                "webhook_events": WEBHOOK_EVENTS[:25],
                "api_logs": API_LOGS[:25],
                "guardrails_summary": {
                    "idempotency_keys_cached": len(IDEMPOTENCY_STORE),
                    "processed_webhook_events": len(PROCESSED_WEBHOOK_EVENTS),
                    "async_fulfillment_jobs": len(ASYNC_FULFILLMENT_QUEUE),
                },
            })
            return

        if path == "/api/stripe/webhooks":
            self._send_json({
                "events": WEBHOOK_EVENTS[:30],
                "api_logs": API_LOGS[:30],
                "processed_events": list(PROCESSED_WEBHOOK_EVENTS.values())[:20],
                "async_fulfillment_queue": ASYNC_FULFILLMENT_QUEUE[:20],
                "idempotency_store": [
                    {
                        "idempotency_key": k,
                        "order_id": v.get("order_id"),
                        "attempt_no": v.get("attempt_no"),
                        "payment_intent_id": v.get("payment_intent_id"),
                        "created_at": v.get("created_at"),
                        "ttl_expires_at": v.get("created_at", 0) + 86400,
                        "param_hash": v.get("param_hash"),
                    }
                    for k, v in list(IDEMPOTENCY_STORE.items())[:20]
                ],
            })
            return

        # Best Practice #6: List PaymentIntents with Cursor Pagination (starting_after) & expand[]
        if path == "/api/stripe/payment_intents":
            limit = max(1, min(25, int(query_params.get("limit", ["5"])[0])))
            starting_after = query_params.get("starting_after", [None])[0]
            expand_list = query_params.get("expand[]", []) + query_params.get("expand", [])

            all_pis = list(reversed(list(PAYMENT_INTENTS_STORE.values())))
            start_idx = 0
            if starting_after:
                for idx, item in enumerate(all_pis):
                    if item["id"] == starting_after:
                        start_idx = idx + 1
                        break

            sliced = all_pis[start_idx : start_idx + limit]
            has_more = (start_idx + limit) < len(all_pis)
            next_cursor = sliced[-1]["id"] if sliced and has_more else None

            hydrated_data = []
            for pi_item in sliced:
                pi_copy = json.loads(json.dumps(pi_item))
                if "latest_charge.balance_transaction" in expand_list:
                    gross = pi_copy.get("amount_received") or pi_copy.get("amount", 0)
                    fee = int(round(gross * 0.029 + 30)) if gross > 0 else 0
                    pi_copy["latest_charge"] = {
                        "id": pi_copy.get("latest_charge_id", gen_stripe_id("ch_3Q9", 18)),
                        "object": "charge",
                        "amount": gross,
                        "currency": pi_copy.get("currency", "usd"),
                        "paid": pi_copy.get("status") == "succeeded",
                        "metadata": pi_copy.get("metadata", {}),
                        "balance_transaction": {
                            "id": gen_stripe_id("txn_3Q9", 18),
                            "object": "balance_transaction",
                            "amount": gross,
                            "fee": fee,
                            "net": max(0, gross - fee),
                            "currency": pi_copy.get("currency", "usd"),
                            "exchange_rate": pi_copy.get("adaptive_pricing", {}).get("exchange_rate", 1.0),
                            "type": "charge",
                        },
                    }
                if "customer" in expand_list:
                    pi_copy["customer"] = {
                        "id": "cus_Q9AetheriaDemoStudio",
                        "object": "customer",
                        "email": pi_copy.get("receipt_email", "alex.rivera@studio-aetheria.io"),
                        "name": "Aetheria Mastering Studios GmbH",
                        "metadata": pi_copy.get("metadata", {}),
                    }
                hydrated_data.append(pi_copy)

            curl_cmd = (
                f"curl -G https://api.stripe.com/v1/payment_intents \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -d limit={limit}"
                + (f" \\\n  -d starting_after={starting_after}" if starting_after else "")
                + "".join(f" \\\n  -d 'expand[]={ex}'" for ex in expand_list)
            )
            resp_obj = {
                "object": "list",
                "url": "/v1/payment_intents",
                "has_more": has_more,
                "next_cursor": next_cursor,
                "starting_after_used": starting_after,
                "expanded_fields": expand_list,
                "single_http_roundtrip": True,
                "n_plus_1_calls_avoided": 2 * len(hydrated_data) if expand_list else 0,
                "data": hydrated_data,
            }
            record_api_log("GET", "/v1/payment_intents", {"limit": limit, "starting_after": starting_after, "expand": expand_list}, resp_obj, 200, 52, curl_cmd)
            self._send_json(resp_obj)
            return

        if path == "/api/stripe/billing/usage":
            overage_sec = max(0, METER_USAGE_STATE["current_period_seconds"] - METER_USAGE_STATE["included_seconds"])
            overage_cents = int(round((overage_sec / 100.0) * METER_USAGE_STATE["rate_usd_cents_per_100s"]))
            base_cents = 3900
            self._send_json({
                "meter": METER_USAGE_STATE,
                "invoice_preview": {
                    "id": "in_preview_1Q9NeuralCloud",
                    "object": "invoice",
                    "customer": METER_USAGE_STATE["customer_id"],
                    "subscription": METER_USAGE_STATE["subscription_id"],
                    "base_subscription_usd_cents": base_cents,
                    "included_seconds": METER_USAGE_STATE["included_seconds"],
                    "total_seconds_used": METER_USAGE_STATE["current_period_seconds"],
                    "overage_seconds": overage_sec,
                    "metered_overage_usd_cents": overage_cents,
                    "upcoming_total_usd_cents": base_cents + overage_cents,
                    "stability_buffer_status": "active_locked_350bps",
                },
            })
            return

        # Serve static files
        self._serve_static_asset(path)
        return

    def do_POST(self) -> None:
        path, _ = self._resolve_request_path_and_query()
        body = self._read_json_body()

        # 1. Runtime API Configuration (Sandbox vs Live Stripe API Key)
        if path == "/api/config":
            mode = body.get("mode", "sandbox_simulator")
            pk = body.get("publishable_key", "").strip()
            sk = body.get("secret_key", "").strip()
            RUNTIME_CONFIG["mode"] = mode
            if pk:
                RUNTIME_CONFIG["publishable_key"] = pk
            if sk:
                RUNTIME_CONFIG["secret_key"] = sk
            self._send_json({
                "status": "updated",
                "mode": RUNTIME_CONFIG["mode"],
                "publishable_key": RUNTIME_CONFIG["publishable_key"],
                "has_secret_key": bool(RUNTIME_CONFIG.get("secret_key")),
            })
            return

        # 2. Quote, Adaptive Pricing & Stripe Tax Calculation
        if path == "/api/stripe/tax/calculations":
            items = body.get("items", [])
            locale_code = body.get("locale", "US")
            vat_id = body.get("vat_id", "")
            postal_code = body.get("postal_code", "10001")
            apply_buffer = bool(body.get("apply_stability_buffer", True))

            result = calculate_cart_pricing_and_tax(items, locale_code, vat_id, postal_code, apply_buffer)
            tax_obj = result["tax_calculation"]

            curl_cmd = (
                f"curl https://api.stripe.com/v1/tax/calculations \\\n"
                f"  -u {RUNTIME_CONFIG['publishable_key'][:12]}...: \\\n"
                f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
                f"  -d currency={tax_obj['currency']} \\\n"
                f"  -d 'customer_details[address][country]={result['profile']['country']}' \\\n"
                f"  -d 'customer_details[address][postal_code]={postal_code}'"
            )
            record_api_log(
                "POST",
                "/v1/tax/calculations",
                {
                    "currency": tax_obj["currency"],
                    "customer_details": tax_obj["customer_details"],
                    "line_items_count": len(items),
                    "adaptive_pricing": {"enabled": True, "stability_buffer": apply_buffer},
                },
                tax_obj,
                200,
                84,
                curl_cmd,
            )
            emit_webhook_event("tax.calculation.created", tax_obj)
            self._send_json(result)
            return

        # 3. Create & Confirm PaymentIntent / Checkout Session (OCS + Radar + 3DS2 + Connect Splits + 7 Best Practices)
        if path == "/api/stripe/payment_intents":
            # BEST PRACTICE #1: Zero Trust on Client-Side Amounts
            has_tampered_root_amount = any(k in body for k in ("amount", "price", "unit_amount", "total"))
            has_tampered_item_amount = any(
                isinstance(it, dict) and any(k in it for k in ("amount", "price", "unit_amount"))
                for it in body.get("items", [])
            )
            if has_tampered_root_amount or has_tampered_item_amount:
                tampered_val = body.get("amount") or body.get("price") or "item-level price override"
                err_resp = {
                    "error": {
                        "type": "invalid_request_error",
                        "code": "zero_trust_client_amount_rejected",
                        "message": (
                            f"SECURITY GUARDRAIL #1 TRIGGERED: Client-side price/amount parameter ({tampered_val}) rejected! "
                            "Never accept amount or price from the browser request body. Send only sku_id + quantity; "
                            "the server computes canonical integer minor units from the server-side CATALOG."
                        ),
                        "param": "amount",
                    }
                }
                record_api_log("POST", "/v1/payment_intents [REJECTED: CLIENT AMOUNT TAMPERING]", body, err_resp, 400, 14, "# Blocked by Zero-Trust Server Guardrail")
                self._send_json(err_resp, status=400)
                return

            items = body.get("items", [])
            locale_code = body.get("locale", "US")
            vat_id = body.get("vat_id", "")
            postal_code = body.get("postal_code", "10001")
            payment_method_type = body.get("payment_method_type", "card")
            test_scenario = body.get("test_scenario", "success_standard")
            customer_email = body.get("email", "alex.rivera@studio-aetheria.io")
            link_instant = bool(body.get("link_instant", False))
            capture_method = body.get("capture_method", "automatic")
            setup_future_usage = body.get("setup_future_usage", None)
            expand_fields = body.get("expand", ["latest_charge.balance_transaction"])

            # BEST PRACTICE #2: Deterministic Idempotency-Key (pi_create_{order_id}_attempt_{attempt_no})
            order_id = str(body.get("order_id") or f"ord_{gen_stripe_id('aeth', 8)}")
            attempt_no = int(body.get("attempt_no", 1))
            header_idem_key = self.headers.get("Idempotency-Key", "").strip()
            idem_key = header_idem_key or str(body.get("idempotency_key") or f"pi_create_{order_id}_attempt_{attempt_no}")

            canonical_params_str = json.dumps(
                {
                    "items": sorted(
                        [{"id": i.get("id", i.get("sku_id", "")), "quantity": int(i.get("quantity", 1))} for i in items],
                        key=lambda x: x["id"],
                    ),
                    "locale": locale_code,
                    "payment_method_type": payment_method_type,
                    "capture_method": capture_method,
                },
                sort_keys=True,
            )
            param_hash = hashlib.sha256(canonical_params_str.encode("utf-8")).hexdigest()[:24]
            now_ts = int(time.time())

            existing_idem = IDEMPOTENCY_STORE.get(idem_key)
            if existing_idem and (now_ts - existing_idem["created_at"]) < 86400:
                if existing_idem["param_hash"] != param_hash:
                    mismatch_err = {
                        "error": {
                            "type": "idempotency_error",
                            "code": "idempotency_key_in_use_with_different_params",
                            "message": (
                                f"Keys for idempotent requests can only be used with the same parameters they were first used with. "
                                f"Idempotency-Key '{idem_key}' was already registered (24h TTL window) with hash {existing_idem['param_hash']}, "
                                f"but received modified parameters ({param_hash}). Increment attempt_no or issue a new order_id."
                            ),
                            "idempotency_key": idem_key,
                            "original_param_hash": existing_idem["param_hash"],
                            "new_param_hash": param_hash,
                            "ttl_seconds_remaining": 86400 - (now_ts - existing_idem["created_at"]),
                        }
                    }
                    record_api_log("POST", f"/v1/payment_intents [IDEMPOTENCY 400 MISMATCH: {idem_key}]", body, mismatch_err, 400, 18, f"# HTTP 400 idempotency_error on {idem_key}")
                    self._send_json(mismatch_err, status=400)
                    return

                # Identical parameters -> Safe Idempotent Replay from 24h cache (Zero Double Charge!)
                cached_resp = json.loads(json.dumps(existing_idem["response_payload"]))
                cached_resp["idempotent_replay"] = True
                cached_resp["idempotency_metadata"] = {
                    "idempotency_key": idem_key,
                    "replayed_from_cache": True,
                    "original_request_id": existing_idem["request_id"],
                    "ttl_seconds_remaining": 86400 - (now_ts - existing_idem["created_at"]),
                    "double_charge_prevented": True,
                }
                record_api_log(
                    "POST",
                    f"/v1/payment_intents [IDEMPOTENT REPLAY: {idem_key}]",
                    body,
                    cached_resp,
                    existing_idem["status_code"],
                    9,
                    f"# Replayed cached response for Idempotency-Key: {idem_key}",
                )
                self._send_json(cached_resp, status=existing_idem["status_code"])
                return

            # BEST PRACTICE #5: Granular Stripe Exception Taxonomy (429 RateLimitError & 503 APIConnectionError vs 402 CardError)
            if test_scenario in ("rate_limit_429", "api_connection_error"):
                is_429 = test_scenario == "rate_limit_429"
                err_code = 429 if is_429 else 503
                exc_class = "stripe.error.RateLimitError" if is_429 else "stripe.error.APIConnectionError"
                transient_err = {
                    "error": {
                        "type": "rate_limit_error" if is_429 else "api_connection_error",
                        "code": "lock_timeout" if is_429 else "network_socket_timeout",
                        "message": (
                            "Too many requests hitting object lock; retry with exponential backoff + jitter using the SAME Idempotency-Key."
                            if is_429
                            else "Transient TLS socket reset before response received; safe to auto-retry with the SAME Idempotency-Key."
                        ),
                        "exception_taxonomy": {
                            "python_sdk_class": exc_class,
                            "http_status": err_code,
                            "category": "transient_infrastructure_error",
                            "should_auto_retry": True,
                            "max_network_retries": 2,
                            "backoff_schedule_ms": [250, 620],
                            "idempotency_key_Action": f"REUSE SAME KEY ({idem_key}) so Stripe deduplicates if first packet reached server",
                        },
                    }
                }
                record_api_log("POST", f"/v1/payment_intents [{exc_class}]", body, transient_err, err_code, 45, f"# Transient {exc_class} — auto-retry with same Idempotency-Key: {idem_key}")
                self._send_json(transient_err, status=err_code)
                return

            calc = calculate_cart_pricing_and_tax(items, locale_code, vat_id, postal_code, True)
            pi_id = gen_stripe_id("pi_3Q9", 21)
            client_secret = f"{pi_id}_secret_{gen_stripe_id('sec', 16)}"
            transfer_group = f"ORDER_{gen_stripe_id('GRP', 8)}"
            req_id = gen_stripe_id("req", 14)

            # BEST PRACTICE #7: Structured metadata propagation for downstream Webhooks & BigQuery Data Pipeline joins
            custom_meta = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
            structured_metadata = {
                "order_id": custom_meta.get("order_id", order_id),
                "customer_tier": custom_meta.get("customer_tier", "enterprise"),
                "erp_cost_center": custom_meta.get("erp_cost_center", "IT-01"),
                "checkout_locale": locale_code,
                "idempotency_attempt": str(attempt_no),
            }
            calc["tax_calculation"]["metadata"] = structured_metadata

            total_app_fee = sum(t["application_fee_amount"] for t in calc["connect_transfers"])

            # Optional live Stripe API passthrough if user enabled live_stripe_api mode
            live_resp = forward_to_live_stripe_if_configured(
                "/v1/payment_intents",
                {
                    "amount": calc["total_local"],
                    "currency": calc["profile"]["currency"],
                    "automatic_payment_methods[enabled]": "true",
                    "description": f"Aetheria Store Order ({len(items)} items)",
                    "receipt_email": customer_email,
                    "metadata[order_id]": structured_metadata["order_id"],
                    "metadata[customer_tier]": structured_metadata["customer_tier"],
                    "metadata[erp_cost_center]": structured_metadata["erp_cost_center"],
                },
            )

            if test_scenario == "radar_block":
                status = "requires_payment_method"
                risk_score = 94
                risk_level = "highest"
                radar_rule = "block_if_risk_score_gt_85 :: High-velocity anonymous proxy IP + mismatched BIN country"
                last_error = {
                    "code": "card_declined",
                    "decline_code": "fraudulent",
                    "message": "Stripe Radar blocked this payment due to elevated fraud risk (Risk Score: 94/100).",
                    "type": "card_error",
                    "exception_taxonomy": {
                        "python_sdk_class": "stripe.error.CardError",
                        "http_status": 402,
                        "category": "business_decline_permanent",
                        "should_auto_retry": False,
                        "idempotency_key_action": f"DO NOT AUTO-RETRY. Prompt customer for a new PaymentMethod and increment attempt_no -> pi_create_{order_id}_attempt_{attempt_no + 1}",
                    },
                }
                next_action = None
            elif test_scenario == "decline_insufficient":
                status = "requires_payment_method"
                risk_score = 19
                risk_level = "normal"
                radar_rule = "allow_standard_velocity"
                last_error = {
                    "code": "card_declined",
                    "decline_code": "insufficient_funds",
                    "message": "Your card has insufficient funds to complete this purchase.",
                    "type": "card_error",
                    "exception_taxonomy": {
                        "python_sdk_class": "stripe.error.CardError",
                        "http_status": 402,
                        "category": "business_decline_insufficient_funds",
                        "should_auto_retry": False,
                        "idempotency_key_action": f"DO NOT AUTO-RETRY. Return user-friendly message to frontend; increment attempt_no -> pi_create_{order_id}_attempt_{attempt_no + 1} on new card.",
                    },
                }
                next_action = None
            elif test_scenario == "3ds2_challenge" and payment_method_type == "card":
                status = "requires_action"
                risk_score = 42
                risk_level = "elevated"
                radar_rule = "request_3ds2_if_risk_score_gt_35 :: PSD2 Strong Customer Authentication required"
                last_error = None
                next_action = {
                    "type": "use_stripe_sdk",
                    "use_stripe_sdk": {
                        "type": "three_d_secure_redirect",
                        "stripe_js": f"https://hooks.stripe.com/3d_secure_2/challenge/{pi_id}",
                        "directory_server_name": "visa_emv_3ds2_v2.2",
                        "banking_app_biometric": True,
                    },
                }
            elif test_scenario == "async_processing" or payment_method_type in ("sepa_debit", "us_bank_account", "konbini"):
                status = "processing"
                risk_score = 9
                risk_level = "normal"
                radar_rule = "allow_verified_bank_mandate_ach_sepa"
                last_error = None
                next_action = None
            elif capture_method == "manual":
                status = "requires_capture"
                risk_score = 10
                risk_level = "normal"
                radar_rule = "pass_pre_auth_hold_7_days"
                last_error = None
                next_action = None
            else:
                status = "succeeded"
                risk_score = 6 if link_instant or payment_method_type != "card" else 11
                risk_level = "normal"
                radar_rule = "pass_network_token_and_link_verified"
                last_error = None
                next_action = None

            is_bridge_crypto = payment_method_type in ("crypto_bridge", "crypto_usdc", "crypto") or bool(body.get("bridge_asset"))
            bridge_asset = body.get("bridge_asset", "usdc" if calc["profile"]["currency"] != "eur" else "eurc").lower()
            bridge_chain = body.get("bridge_chain", "base").lower()
            bridge_settlement = body.get("bridge_settlement_mode", "auto_fiat_liquidation")

            bridge_details = None
            if is_bridge_crypto:
                usd_equiv = (calc["total_local"] / calc["profile"]["fx_rate"]) if not calc["profile"]["zero_decimal"] else (calc["total_local"] / calc["profile"]["fx_rate"]) * 100
                stable_units = round(usd_equiv / 100.0, 2) if bridge_asset != "eurc" else round((usd_equiv * 0.92) / 100.0, 2)
                if bridge_chain == "solana":
                    dep_addr = f"Brdg{gen_stripe_id('Sol', 28).replace('_', '')}"
                elif bridge_chain == "stellar":
                    dep_addr = f"GBRDG{gen_stripe_id('STLR', 28).replace('_', '').upper()}"
                else:
                    dep_addr = f"0x8F4e{hashlib.sha256(pi_id.encode()).hexdigest()[:36]}"

                bridge_details = {
                    "orchestrator": "Bridge (a Stripe company) — v0 Orchestration API",
                    "bridge_transfer_id": gen_stripe_id("br_tr_1Q9", 16),
                    "liquidation_address_id": gen_stripe_id("br_liq_1Q9", 16),
                    "onchain_deposit_address": dep_addr,
                    "source_asset": bridge_asset.upper(),
                    "source_chain": bridge_chain,
                    "stablecoin_amount_paid": f"{stable_units:.2f} {bridge_asset.upper()}",
                    "destination_settlement_mode": bridge_settlement,
                    "destination_currency": calc["profile"]["currency"].upper() if bridge_settlement == "auto_fiat_liquidation" else "USDB (Stripe Stablecoin Financial Account)",
                    "bridge_orchestration_fee_bps": 50,
                    "paymaster_gas_sponsored": True,
                    "tx_hash": f"0x{hashlib.sha256(f'{pi_id}:{bridge_chain}'.encode()).hexdigest()[:48]}",
                    "finality_ms": 420 if bridge_chain == "solana" else 1650,
                }

            # BEST PRACTICE #6: Hydrate latest_charge.balance_transaction via expand[] in 1 HTTP call
            charge_id = gen_stripe_id("ch_3Q9", 18)
            txn_id = gen_stripe_id("txn_3Q9", 18)
            gross_amt = calc["total_local"] if status == "succeeded" else 0
            stripe_fee_amt = int(round(gross_amt * 0.029 + 30)) if gross_amt > 0 else 0
            expanded_charge = None
            if status == "succeeded":
                if "latest_charge.balance_transaction" in expand_fields:
                    expanded_charge = {
                        "id": charge_id,
                        "object": "charge",
                        "amount": gross_amt,
                        "currency": calc["profile"]["currency"],
                        "paid": True,
                        "status": "succeeded",
                        "metadata": structured_metadata,
                        "balance_transaction": {
                            "id": txn_id,
                            "object": "balance_transaction",
                            "amount": gross_amt,
                            "fee": stripe_fee_amt,
                            "net": max(0, gross_amt - stripe_fee_amt),
                            "currency": calc["profile"]["currency"],
                            "exchange_rate": calc["fx_quote"]["exchange_rate"],
                            "type": "charge",
                        },
                    }
                else:
                    expanded_charge = charge_id

            pi_object = {
                "id": pi_id,
                "object": "payment_intent",
                "amount": calc["total_local"],
                "amount_capturable": calc["total_local"] if status == "requires_capture" else 0,
                "amount_received": calc["total_local"] if status == "succeeded" else 0,
                "currency": calc["profile"]["currency"],
                "status": status,
                "capture_method": capture_method,
                "setup_future_usage": setup_future_usage,
                "client_secret": client_secret,
                "created": now_ts,
                "customer": "cus_Q9AetheriaDemoStudio",
                "receipt_email": customer_email,
                "metadata": structured_metadata,
                "latest_charge": expanded_charge,
                "latest_charge_id": charge_id,
                "zero_trust_pricing_audit": {
                    "client_amount_accepted": False,
                    "server_catalog_lookup": True,
                    "integer_minor_units": calc["total_local"],
                    "canonical_skus_resolved": [
                        {"sku_id": li["product_id"], "qty": li["quantity"], "unit_minor": li["unit_amount"]}
                        for li in calc["tax_calculation"]["line_items"]
                    ],
                },
                "idempotency_protection": {
                    "idempotency_key": idem_key,
                    "order_id": order_id,
                    "attempt_no": attempt_no,
                    "param_hash": param_hash,
                    "ttl_hours": 24,
                },
                "automatic_payment_methods": {"allow_redirects": "always", "enabled": True},
                "payment_method_types": [m["id"] for m in calc["profile"]["ai_ordered_methods"]],
                "payment_method": gen_stripe_id("pm_1Q9Bridge" if is_bridge_crypto else "pm_1Q9", 18),
                "payment_method_options": {
                    "card": {
                        "request_three_d_secure": "automatic",
                        "network_token": {"used": True, "token_id": gen_stripe_id("ntok_vts", 14)},
                    },
                    "us_bank_account": {"financial_connections": {"permissions": ["payment_method", "balances"]}},
                    "crypto": {
                        "orchestrator": "bridge_v0",
                        "networks": ["base", "solana", "arbitrum", "polygon", "stellar", "ethereum"],
                        "supported_assets": ["usdc", "usdb", "eurc", "pyusd"],
                        "settlement_mode": bridge_settlement,
                    },
                },
                "bridge_stablecoin_details": bridge_details,
                "adaptive_pricing": {
                    "enabled": True,
                    "fx_quote_id": calc["fx_quote"]["id"],
                    "exchange_rate": calc["fx_quote"]["exchange_rate"],
                    "stability_buffer_pct": calc["fx_quote"]["subscription_stability_buffer_pct"],
                },
                "hooks": {
                    "inputs": {"tax": {"calculation": calc["tax_calculation"]["id"]}},
                },
                "radar_evaluation": {
                    "risk_score": 3 if is_bridge_crypto else risk_score,
                    "risk_level": "normal" if is_bridge_crypto else risk_level,
                    "matched_rule": "pass_bridge_onchain_finality_zero_chargeback" if is_bridge_crypto else radar_rule,
                    "network_token_cryptogram": "eip712_permit2_verified" if is_bridge_crypto else "verified_eci_05",
                    "adaptive_acceptance_routed": True,
                    "device_fingerprint": gen_stripe_id("dfp", 16),
                },
                "transfer_group": transfer_group if calc["connect_transfers"] else None,
                "application_fee_amount": total_app_fee if total_app_fee > 0 else None,
                "connect_transfers": calc["connect_transfers"],
                "next_action": next_action,
                "last_payment_error": last_error,
                "live_stripe_passthrough": live_resp,
                "state_history": [
                    {"state": "requires_payment_method", "event": "payment_intent.created"},
                    {"state": "requires_confirmation", "event": "payment_method.attached"},
                    *(
                        [{"state": "processing", "event": "bridge.liquidation_address.deposit_detected"}]
                        if is_bridge_crypto
                        else []
                    ),
                    {"state": status, "event": f"payment_intent.{status}"},
                ],
            }

            PAYMENT_INTENTS_STORE[pi_id] = pi_object

            curl_cmd = (
                f"curl https://api.stripe.com/v1/payment_intents \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
                f"  -H 'Idempotency-Key: {idem_key}' \\\n"
                f"  -d amount={calc['total_local']} \\\n"
                f"  -d currency={calc['profile']['currency']} \\\n"
                f"  -d capture_method={capture_method} \\\n"
                f"  -d 'expand[]=latest_charge.balance_transaction' \\\n"
                f"  -d 'metadata[order_id]={structured_metadata['order_id']}' \\\n"
                f"  -d 'metadata[customer_tier]={structured_metadata['customer_tier']}' \\\n"
                f"  -d 'metadata[erp_cost_center]={structured_metadata['erp_cost_center']}' \\\n"
                f"  -d 'automatic_payment_methods[enabled]=true' \\\n"
                f"  -d 'hooks[inputs][tax][calculation]={calc['tax_calculation']['id']}'"
            )
            if is_bridge_crypto:
                curl_cmd += (
                    f" \\\n  -d 'payment_method_types[]=crypto'"
                    f" \\\n  -d 'payment_method_options[crypto][network]={bridge_chain}'"
                    f" \\\n  -d 'payment_method_options[crypto][asset]={bridge_asset}'"
                )
            if setup_future_usage:
                curl_cmd += f" \\\n  -d setup_future_usage={setup_future_usage}"
            if total_app_fee > 0:
                curl_cmd += f" \\\n  -d application_fee_amount={total_app_fee} \\\n  -d transfer_group={transfer_group}"

            http_code = 402 if last_error else 200
            response_envelope = {
                "payment_intent": pi_object,
                "calculation": calc,
                "idempotent_replay": False,
                "idempotency_metadata": {
                    "idempotency_key": idem_key,
                    "replayed_from_cache": False,
                    "original_request_id": req_id,
                    "ttl_seconds_remaining": 86400,
                },
            }

            # Store in 24-hour Idempotency Store
            IDEMPOTENCY_STORE[idem_key] = {
                "created_at": now_ts,
                "param_hash": param_hash,
                "order_id": order_id,
                "attempt_no": attempt_no,
                "payment_intent_id": pi_id,
                "request_id": req_id,
                "status_code": http_code,
                "response_payload": response_envelope,
            }

            record_api_log(
                "POST",
                "/v1/payment_intents",
                {
                    "idempotency_key": idem_key,
                    "amount_computed_server_side": calc["total_local"],
                    "currency": calc["profile"]["currency"],
                    "capture_method": capture_method,
                    "expand": expand_fields,
                    "metadata": structured_metadata,
                    "setup_future_usage": setup_future_usage,
                    "payment_method_type": payment_method_type,
                    "bridge_stablecoin": bridge_details,
                    "tax_calculation": calc["tax_calculation"]["id"],
                    "application_fee_amount": total_app_fee or None,
                    "transfer_group": transfer_group if calc["connect_transfers"] else None,
                },
                pi_object,
                http_code,
                142,
                curl_cmd,
            )

            emit_webhook_event("payment_intent.created", pi_object, request_id=req_id)
            if is_bridge_crypto and bridge_details:
                emit_webhook_event("bridge.liquidation_address.deposit_detected", bridge_details, request_id=req_id)
                emit_webhook_event("bridge.transfer.completed", bridge_details, request_id=req_id)
            if status == "succeeded":
                emit_webhook_event("payment_intent.succeeded", pi_object, request_id=req_id)
                emit_webhook_event(
                    "tax.transaction.created",
                    {
                        "id": gen_stripe_id("tax_txn_1Q9", 18),
                        "object": "tax.transaction",
                        "calculation": calc["tax_calculation"]["id"],
                        "reference": pi_id,
                        "tax_amount": calc["tax_local"],
                        "currency": calc["profile"]["currency"],
                        "metadata": structured_metadata,
                    },
                    request_id=req_id,
                )
                for tr in calc["connect_transfers"]:
                    emit_webhook_event(
                        "transfer.created",
                        {
                            "id": gen_stripe_id("tr_3Q9", 18),
                            "object": "transfer",
                            "amount": tr["net_transfer_amount"],
                            "currency": tr["currency"],
                            "destination": tr["destination_account"],
                            "transfer_group": transfer_group,
                            "source_transaction": pi_id,
                            "metadata": structured_metadata,
                            "description": f"Split payout for {tr['product_name']} ({tr['seller_name']})",
                        },
                        request_id=req_id,
                    )
                if calc["has_subscription"]:
                    emit_webhook_event(
                        "customer.subscription.created",
                        {
                            "id": gen_stripe_id("sub_1Q9", 18),
                            "object": "subscription",
                            "customer": "cus_Q9AetheriaDemoStudio",
                            "status": "active",
                            "currency": calc["profile"]["currency"],
                            "metadata": structured_metadata,
                            "adaptive_pricing": {
                                "stability_buffer_enabled": True,
                                "buffer_bps": int(calc["profile"]["stability_buffer_pct"] * 100),
                            },
                            "items": ["price_1Q9NeuralCloudProMonthly", "mtr_1Q9NeuralDSPComputeSec"],
                        },
                        request_id=req_id,
                    )
            elif status == "requires_capture":
                emit_webhook_event("payment_intent.amount_capturable_updated", pi_object, request_id=req_id)
            elif status == "processing":
                emit_webhook_event("payment_intent.processing", pi_object, request_id=req_id)
            elif status == "requires_action":
                emit_webhook_event("payment_intent.requires_action", pi_object, request_id=req_id)
            else:
                if test_scenario == "radar_block":
                    emit_webhook_event(
                        "radar.early_fraud_warning.created",
                        {
                            "id": gen_stripe_id("issfr_1Q9", 18),
                            "object": "radar.early_fraud_warning",
                            "payment_intent": pi_id,
                            "fraud_type": "unauthorized_use_of_card",
                            "risk_score": risk_score,
                            "actionable": True,
                        },
                        request_id=req_id,
                    )
                emit_webhook_event("payment_intent.payment_failed", pi_object, request_id=req_id)

            self._send_json(response_envelope, status=http_code)
            return

        # 4. Complete EMV 3D Secure 2 (3DS2) Step-Up Challenge
        if path == "/api/stripe/payment_intents/confirm_3ds":
            pi_id = body.get("payment_intent_id", "")
            otp_code = body.get("otp_code", "849201")
            pi_obj = PAYMENT_INTENTS_STORE.get(pi_id)
            if not pi_obj:
                self._send_json({"error": {"message": f"PaymentIntent {pi_id} not found"}}, status=404)
                return

            if pi_obj.get("capture_method") == "manual":
                pi_obj["status"] = "requires_capture"
                pi_obj["amount_capturable"] = pi_obj["amount"]
            else:
                pi_obj["status"] = "succeeded"
                pi_obj["amount_received"] = pi_obj["amount"]
            pi_obj["next_action"] = None
            pi_obj["three_d_secure_2_result"] = {
                "authenticated": True,
                "version": "2.2.0",
                "trans_status": "Y",
                "eci": "05",
                "cavv": gen_stripe_id("cavv", 20),
                "liability_shift": "issuer_assumed",
                "otp_verified": otp_code,
            }

            curl_cmd = (
                f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/confirm \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -H 'Stripe-Version: {STRIPE_API_VERSION}'"
            )
            record_api_log(
                "POST",
                f"/v1/payment_intents/{pi_id}/confirm",
                {"payment_intent": pi_id, "three_d_secure_2_challenge": "completed"},
                pi_obj,
                200,
                96,
                curl_cmd,
            )
            emit_webhook_event(f"payment_intent.{pi_obj['status']}", pi_obj)
            if pi_obj["status"] == "succeeded":
                for tr in pi_obj.get("connect_transfers", []):
                    emit_webhook_event(
                        "transfer.created",
                        {
                            "id": gen_stripe_id("tr_3Q9", 18),
                            "object": "transfer",
                            "amount": tr["net_transfer_amount"],
                            "currency": tr["currency"],
                            "destination": tr["destination_account"],
                            "source_transaction": pi_id,
                        },
                    )
            self._send_json({"payment_intent": pi_obj})
            return

        # 4b. Manual Capture (/v1/payment_intents/{id}/capture) — Full or Partial Capture
        if path == "/api/stripe/payment_intents/capture":
            pi_id = body.get("payment_intent_id", "")
            pi_obj = PAYMENT_INTENTS_STORE.get(pi_id)
            if not pi_obj:
                self._send_json({"error": {"message": f"PaymentIntent {pi_id} not found"}}, status=404)
                return
            capture_strategy = body.get("capture_strategy", "")
            if capture_strategy == "partial_75_pct":
                amount_to_capture = int(round(pi_obj["amount"] * 0.75))
            elif capture_strategy == "full":
                amount_to_capture = int(pi_obj["amount"])
            else:
                amount_to_capture = int(body.get("amount_to_capture", pi_obj["amount"]))
            amount_to_capture = min(amount_to_capture, pi_obj["amount"])
            pi_obj["status"] = "succeeded"
            pi_obj["amount_received"] = amount_to_capture
            pi_obj["amount_capturable"] = 0
            pi_obj["latest_charge"] = gen_stripe_id("ch_3Q9", 20)
            pi_obj["balance_transaction"] = {
                "id": gen_stripe_id("txn_3Q9", 20),
                "gross": amount_to_capture,
                "fee": int(round(amount_to_capture * 0.029 + 30)),
                "net": amount_to_capture - int(round(amount_to_capture * 0.029 + 30)),
                "currency": pi_obj["currency"],
            }
            curl_cmd = (
                f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/capture \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -d amount_to_capture={amount_to_capture}"
            )
            record_api_log(
                "POST",
                f"/v1/payment_intents/{pi_id}/capture",
                {"amount_to_capture": amount_to_capture, "capture_strategy": capture_strategy or "explicit"},
                pi_obj,
                200,
                88,
                curl_cmd,
            )
            emit_webhook_event("payment_intent.succeeded", pi_obj)
            emit_webhook_event("charge.captured", pi_obj)
            self._send_json({"payment_intent": pi_obj})
            return

        # 4c. Cancel PaymentIntent / Void Hold (/v1/payment_intents/{id}/cancel)
        if path == "/api/stripe/payment_intents/cancel":
            pi_id = body.get("payment_intent_id", "")
            reason = body.get("cancellation_reason", "requested_by_customer")
            pi_obj = PAYMENT_INTENTS_STORE.get(pi_id)
            if not pi_obj:
                self._send_json({"error": {"message": f"PaymentIntent {pi_id} not found"}}, status=404)
                return
            pi_obj["status"] = "canceled"
            pi_obj["amount_capturable"] = 0
            pi_obj["canceled_at"] = int(time.time())
            pi_obj["cancellation_reason"] = reason
            curl_cmd = (
                f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/cancel \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -d cancellation_reason={reason}"
            )
            record_api_log(
                "POST",
                f"/v1/payment_intents/{pi_id}/cancel",
                {"cancellation_reason": reason},
                pi_obj,
                200,
                74,
                curl_cmd,
            )
            emit_webhook_event("payment_intent.canceled", pi_obj)
            self._send_json({"payment_intent": pi_obj})
            return

        # 4d. Refunds & Proportional Connect Transfer Reversal (/v1/refunds)
        if path == "/api/stripe/refunds":
            pi_id = body.get("payment_intent_id", "")
            pi_obj = PAYMENT_INTENTS_STORE.get(pi_id)
            refund_strategy = body.get("refund_strategy", "")
            if refund_strategy == "full" and pi_obj:
                refund_amount = int(pi_obj["amount_received"] or pi_obj["amount"])
            else:
                refund_amount = int(body.get("amount", pi_obj["amount_received"] if pi_obj else 42000))
            reverse_transfer = bool(body.get("reverse_transfer", True))
            refund_app_fee = bool(body.get("refund_application_fee", True))
            refund_obj = {
                "id": gen_stripe_id("re_3Q9", 20),
                "object": "refund",
                "amount": refund_amount,
                "currency": pi_obj["currency"] if pi_obj else "usd",
                "payment_intent": pi_id or gen_stripe_id("pi_3Q9", 20),
                "status": "succeeded",
                "reason": body.get("reason", "requested_by_customer"),
                "reverse_transfer": reverse_transfer,
                "refund_application_fee": refund_app_fee,
                "transfer_reversal": gen_stripe_id("trr_1Q9", 18) if reverse_transfer else None,
                "metadata": pi_obj.get("metadata", {}) if pi_obj else {},
            }
            if pi_obj:
                pi_obj["refunded"] = True
                pi_obj["amount_refunded"] = refund_amount
            curl_cmd = (
                f"curl https://api.stripe.com/v1/refunds \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -d payment_intent={refund_obj['payment_intent']} \\\n"
                f"  -d amount={refund_amount} \\\n"
                f"  -d reverse_transfer={'true' if reverse_transfer else 'false'} \\\n"
                f"  -d refund_application_fee={'true' if refund_app_fee else 'false'}"
            )
            record_api_log("POST", "/v1/refunds", body, refund_obj, 200, 92, curl_cmd)
            emit_webhook_event("charge.refunded", refund_obj)
            self._send_json({"refund": refund_obj, "payment_intent": pi_obj})
            return

        # 4e. Interactive Step-by-Step Payment State Machine Sandbox (/api/stripe/state_machine/step)
        if path == "/api/stripe/state_machine/step":
            action = body.get("action", "create")
            pi_id = body.get("payment_intent_id", "")
            pi_obj = PAYMENT_INTENTS_STORE.get(pi_id)

            if action == "create" or not pi_obj:
                pi_id = gen_stripe_id("pi_3Q9StateLab", 16)
                pi_obj = {
                    "id": pi_id,
                    "object": "payment_intent",
                    "amount": 84900,
                    "amount_capturable": 0,
                    "amount_received": 0,
                    "currency": "usd",
                    "status": "requires_payment_method",
                    "capture_method": body.get("capture_method", "automatic"),
                    "setup_future_usage": "off_session",
                    "client_secret": f"{pi_id}_secret_{gen_stripe_id('sec', 14)}",
                    "customer": "cus_Q9AetheriaDemoStudio",
                    "payment_method": None,
                    "hooks": {"inputs": {"tax": {"calculation": gen_stripe_id("taxcalc_1Q9", 14)}}},
                    "radar_evaluation": {"risk_score": None, "status": "pending_payment_method"},
                    "state_history": [
                        {"step": 1, "state": "requires_payment_method", "note": "PaymentIntent initialized via POST /v1/payment_intents"}
                    ],
                }
                PAYMENT_INTENTS_STORE[pi_id] = pi_obj
                curl_cmd = (
                    "curl https://api.stripe.com/v1/payment_intents \\\n"
                    "  -u sk_test_...: \\\n"
                    "  -d amount=84900 -d currency=usd \\\n"
                    f"  -d capture_method={pi_obj['capture_method']} \\\n"
                    "  -d setup_future_usage=off_session"
                )
                record_api_log("POST", "/v1/payment_intents", {"amount": 84900, "currency": "usd", "status": "requires_payment_method"}, pi_obj, 200, 72, curl_cmd)
                emit_webhook_event("payment_intent.created", pi_obj)

            elif action == "attach_pm":
                pm_id = gen_stripe_id("pm_1Q9NetToken", 16)
                pi_obj["payment_method"] = pm_id
                pi_obj["status"] = "requires_confirmation"
                pi_obj["network_token"] = {"id": gen_stripe_id("ntok_vts", 14), "cryptogram": "eci_05_dynamic", "brand": "visa"}
                pi_obj["state_history"].append(
                    {"step": 2, "state": "requires_confirmation", "note": f"Attached tokenized PaymentMethod {pm_id} (PCI SAQ-A)"}
                )
                curl_cmd = (
                    f"curl https://api.stripe.com/v1/payment_intents/{pi_id} \\\n"
                    f"  -u sk_test_...: \\\n"
                    f"  -d payment_method={pm_id}"
                )
                record_api_log("POST", f"/v1/payment_intents/{pi_id}", {"payment_method": pm_id}, pi_obj, 200, 64, curl_cmd)
                emit_webhook_event("payment_method.attached", {"id": pm_id, "customer": pi_obj["customer"], "network_token": pi_obj["network_token"]})

            elif action == "require_3ds2":
                pi_obj["status"] = "requires_action"
                pi_obj["radar_evaluation"] = {"risk_score": 44, "risk_level": "elevated", "rule": "request_3ds2_if_risk_gt_35"}
                pi_obj["next_action"] = {
                    "type": "use_stripe_sdk",
                    "directory_server": "visa_emv_3ds2_v2.2",
                    "challenge_url": f"https://hooks.stripe.com/3d_secure_2/challenge/{pi_id}",
                }
                pi_obj["state_history"].append(
                    {"step": 3, "state": "requires_action", "note": "Radar triggered EMV 3DS2 Step-Up Challenge (PSD2 SCA)"}
                )
                curl_cmd = f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/confirm -u sk_test_...:"
                record_api_log("POST", f"/v1/payment_intents/{pi_id}/confirm", {"request_three_d_secure": "any"}, pi_obj, 200, 108, curl_cmd)
                emit_webhook_event("payment_intent.requires_action", pi_obj)

            elif action == "async_processing":
                pi_obj["status"] = "processing"
                pi_obj["payment_method_types"] = ["sepa_debit", "us_bank_account"]
                pi_obj["next_action"] = None
                pi_obj["state_history"].append(
                    {"step": 4, "state": "processing", "note": "Submitted to ACH / SEPA clearing rails (T+2 async settlement)"}
                )
                curl_cmd = f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/confirm -u sk_test_...: -d payment_method_types[]=sepa_debit"
                record_api_log("POST", f"/v1/payment_intents/{pi_id}/confirm", {"async_rail": "sepa_debit"}, pi_obj, 200, 95, curl_cmd)
                emit_webhook_event("payment_intent.processing", pi_obj)

            elif action == "authorize_hold":
                pi_obj["capture_method"] = "manual"
                pi_obj["status"] = "requires_capture"
                pi_obj["amount_capturable"] = pi_obj["amount"]
                pi_obj["next_action"] = None
                pi_obj["radar_evaluation"] = {"risk_score": 11, "risk_level": "normal", "liability_shift": True}
                pi_obj["state_history"].append(
                    {"step": 5, "state": "requires_capture", "note": "Funds authorized & held on card (amount_capturable=84900); awaiting fulfillment capture"}
                )
                curl_cmd = f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/confirm -u sk_test_...: -d capture_method=manual"
                record_api_log("POST", f"/v1/payment_intents/{pi_id}/confirm", {"capture_method": "manual"}, pi_obj, 200, 115, curl_cmd)
                emit_webhook_event("payment_intent.amount_capturable_updated", pi_obj)

            elif action == "capture_succeed":
                pi_obj["status"] = "succeeded"
                pi_obj["amount_received"] = pi_obj["amount"]
                pi_obj["amount_capturable"] = 0
                pi_obj["next_action"] = None
                pi_obj["latest_charge"] = gen_stripe_id("ch_3Q9", 18)
                pi_obj["balance_transaction"] = {
                    "id": gen_stripe_id("txn_3Q9", 18),
                    "gross": 84900,
                    "stripe_fee": 2492,
                    "application_fee": 10188,
                    "net_settled": 82408,
                }
                pi_obj["state_history"].append(
                    {"step": 6, "state": "succeeded", "note": "Funds captured, BalanceTransaction settled, Tax committed & Connect split transferred"}
                )
                curl_cmd = f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/capture -u sk_test_...:"
                record_api_log("POST", f"/v1/payment_intents/{pi_id}/capture", {"amount_to_capture": 84900}, pi_obj, 200, 89, curl_cmd)
                emit_webhook_event("payment_intent.succeeded", pi_obj)
                emit_webhook_event("charge.succeeded", {"id": pi_obj["latest_charge"], "payment_intent": pi_id, "amount": 84900})

            elif action == "decline_recover":
                pi_obj["status"] = "requires_payment_method"
                pi_obj["last_payment_error"] = {
                    "code": "card_declined",
                    "decline_code": "insufficient_funds",
                    "message": "Issuer declined authorization (insufficient_funds). Intent reverted to requires_payment_method for retry.",
                }
                pi_obj["state_history"].append(
                    {"step": 7, "state": "requires_payment_method", "note": "Decline recovery: Intent safely reverted to requires_payment_method without duplicate order"}
                )
                curl_cmd = f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/confirm -u sk_test_...:"
                record_api_log("POST", f"/v1/payment_intents/{pi_id}/confirm", {"simulated_decline": "insufficient_funds"}, pi_obj, 402, 102, curl_cmd)
                emit_webhook_event("payment_intent.payment_failed", pi_obj)

            elif action == "cancel_void":
                pi_obj["status"] = "canceled"
                pi_obj["amount_capturable"] = 0
                pi_obj["cancellation_reason"] = "requested_by_customer"
                pi_obj["state_history"].append(
                    {"step": 8, "state": "canceled", "note": "Authorization hold voided via /cancel (terminal state, $0 interchange fee)"}
                )
                curl_cmd = f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/cancel -u sk_test_...:"
                record_api_log("POST", f"/v1/payment_intents/{pi_id}/cancel", {"cancellation_reason": "requested_by_customer"}, pi_obj, 200, 68, curl_cmd)
                emit_webhook_event("payment_intent.canceled", pi_obj)

            elif action == "dispute_defense":
                dispute_obj = {
                    "id": gen_stripe_id("dp_1Q9", 18),
                    "object": "dispute",
                    "amount": pi_obj["amount"],
                    "currency": pi_obj["currency"],
                    "payment_intent": pi_id,
                    "reason": "fraudulent",
                    "status": "won",
                    "evidence_submitted": {
                        "three_d_secure_cavv": gen_stripe_id("cavv_eci05", 16),
                        "network_token_cryptogram": "verified",
                        "shipping_tracking_number": "DHL-994810294",
                        "liability_shift_applied": True,
                    },
                }
                pi_obj["dispute"] = dispute_obj
                pi_obj["state_history"].append(
                    {"step": 9, "state": "dispute_won", "note": "Dispute automatically won via 3DS2 ECI-05 Liability Shift & Radar Evidence"}
                )
                curl_cmd = f"curl https://api.stripe.com/v1/disputes/{dispute_obj['id']} -u sk_test_...: -d 'evidence[shipping_tracking_number]=DHL-994810294'"
                record_api_log("POST", f"/v1/disputes/{dispute_obj['id']}", dispute_obj["evidence_submitted"], dispute_obj, 200, 118, curl_cmd)
                emit_webhook_event("charge.dispute.created", dispute_obj)
                emit_webhook_event("charge.dispute.closed", dispute_obj)

            elif action == "bridge_stablecoin":
                pi_obj["status"] = "succeeded"
                pi_obj["amount_received"] = pi_obj["amount"]
                pi_obj["amount_capturable"] = 0
                pi_obj["payment_method_types"] = ["crypto"]
                bridge_info = {
                    "orchestrator": "Bridge (a Stripe company) — v0 Orchestration API",
                    "bridge_transfer_id": gen_stripe_id("br_tr_1Q9", 16),
                    "liquidation_address_id": gen_stripe_id("br_liq_1Q9", 16),
                    "onchain_deposit_address": f"0x8F4e{hashlib.sha256(pi_id.encode()).hexdigest()[:36]}",
                    "source_asset": "USDC",
                    "source_chain": "base",
                    "stablecoin_amount_paid": "849.00 USDC",
                    "destination_settlement_mode": "auto_fiat_liquidation",
                    "destination_currency": "USD",
                    "paymaster_gas_sponsored": True,
                    "tx_hash": f"0x{hashlib.sha256(f'{pi_id}:base'.encode()).hexdigest()[:48]}",
                    "finality_ms": 1450,
                }
                pi_obj["bridge_stablecoin_details"] = bridge_info
                pi_obj["state_history"].append(
                    {
                        "step": 10,
                        "state": "succeeded (bridge_stablecoin)",
                        "note": f"Bridge Liquidation Address ({bridge_info['liquidation_address_id']}) settled 849.00 USDC on Base L2 into Stripe USD Balance",
                    }
                )
                curl_cmd = (
                    f"curl https://api.stripe.com/v1/payment_intents/{pi_id}/confirm \\\n"
                    f"  -u sk_test_...: \\\n"
                    f"  -d 'payment_method_types[]=crypto' \\\n"
                    f"  -d 'payment_method_options[crypto][network]=base' \\\n"
                    f"  -d 'payment_method_options[crypto][asset]=usdc'"
                )
                record_api_log("POST", f"/v1/payment_intents/{pi_id}/confirm", {"payment_method_type": "crypto", "bridge": bridge_info}, pi_obj, 200, 94, curl_cmd)
                emit_webhook_event("bridge.liquidation_address.deposit_detected", bridge_info)
                emit_webhook_event("bridge.transfer.completed", bridge_info)
                emit_webhook_event("payment_intent.succeeded", pi_obj)

            self._send_json({"payment_intent": pi_obj})
            return

        # 5. Stripe Billing Meter Events (Metronome-powered /v1/billing/meter_events)
        if path == "/api/stripe/billing/meter_events":
            seconds_to_add = max(100, int(body.get("value", 1250)))
            workload_label = body.get("workload", "Neural 16-Stem Separation & De-Reverb (96kHz)")
            evt_id = gen_stripe_id("mtev_1Q9", 18)
            idem_key = gen_stripe_id("idem_mtr", 16)
            now_ts = int(time.time())

            METER_USAGE_STATE["current_period_seconds"] += seconds_to_add
            meter_event_obj = {
                "id": evt_id,
                "object": "billing.meter_event",
                "event_name": METER_USAGE_STATE["event_name"],
                "timestamp": now_ts,
                "identifier": idem_key,
                "payload": {
                    "stripe_customer_id": METER_USAGE_STATE["customer_id"],
                    "value": str(seconds_to_add),
                    "workload": workload_label,
                },
            }
            METER_USAGE_STATE["events"].insert(
                0,
                {
                    "id": evt_id,
                    "timestamp": now_ts,
                    "value": seconds_to_add,
                    "workload": workload_label,
                    "idempotency_key": idem_key,
                },
            )

            overage_sec = max(0, METER_USAGE_STATE["current_period_seconds"] - METER_USAGE_STATE["included_seconds"])
            overage_cents = int(round((overage_sec / 100.0) * METER_USAGE_STATE["rate_usd_cents_per_100s"]))
            base_cents = 3900

            curl_cmd = (
                f"curl https://api.stripe.com/v1/billing/meter_events \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
                f"  -d event_name={METER_USAGE_STATE['event_name']} \\\n"
                f"  -d 'payload[stripe_customer_id]={METER_USAGE_STATE['customer_id']}' \\\n"
                f"  -d 'payload[value]={seconds_to_add}' \\\n"
                f"  -d identifier={idem_key}"
            )
            record_api_log(
                "POST",
                "/v1/billing/meter_events",
                meter_event_obj["payload"],
                meter_event_obj,
                200,
                58,
                curl_cmd,
            )
            emit_webhook_event("billing.meter_event.ingested", meter_event_obj)
            if overage_sec > 0:
                emit_webhook_event(
                    "invoice.upcoming",
                    {
                        "id": "in_preview_1Q9NeuralCloud",
                        "customer": METER_USAGE_STATE["customer_id"],
                        "subscription": METER_USAGE_STATE["subscription_id"],
                        "amount_due": base_cents + overage_cents,
                        "currency": "usd",
                        "metered_overage_seconds": overage_sec,
                    },
                )

            self._send_json({
                "meter_event": meter_event_obj,
                "meter": METER_USAGE_STATE,
                "invoice_preview": {
                    "base_subscription_usd_cents": base_cents,
                    "included_seconds": METER_USAGE_STATE["included_seconds"],
                    "total_seconds_used": METER_USAGE_STATE["current_period_seconds"],
                    "overage_seconds": overage_sec,
                    "metered_overage_usd_cents": overage_cents,
                    "upcoming_total_usd_cents": base_cents + overage_cents,
                },
            })
            return

        # 6. Stripe Agentic Commerce Toolkit (/v1/agentic/order_intents & Delegated Payment Token)
        if path == "/api/stripe/agentic/order_intents":
            mandate = body.get("mandate", "field_rig_under_1300")
            budget_limit_usd_cents = int(body.get("budget_limit_usd_cents", 130000))
            locale_code = body.get("locale", "US")

            if mandate == "studio_mastering_bundle":
                selected_items = [
                    {"id": "prod_monolith_console", "quantity": 1},
                    {"id": "prod_planar_headphones", "quantity": 1},
                    {"id": "prod_neural_cloud_pro", "quantity": 1},
                ]
                rationale = (
                    "Selected Monolith Tactile Console ($540) + Reference Planar Headphones ($690) "
                    "+ Neural Cloud Pro ($39/mo) for an end-to-end mastering chain within budget."
                )
            elif mandate == "creator_marketplace_rig":
                selected_items = [
                    {"id": "prod_ambernex_dsp", "quantity": 1},
                    {"id": "prod_kyoto_mic", "quantity": 1},
                ]
                rationale = (
                    "Selected Klangwerk AmberNex Euro-DSP ($420) + Kyoto Acoustics Binaural Mic ($380) "
                    "with automated Stripe Connect v2 split payouts to DE and JP creators."
                )
            else:
                selected_items = [
                    {"id": "prod_synth_mk2", "quantity": 1},
                    {"id": "prod_kyoto_mic", "quantity": 1},
                    {"id": "prod_neural_cloud_pro", "quantity": 1},
                ]
                rationale = (
                    "Selected Aetheria Field Synthesizer MK-II ($849) + Kyoto Binaural Field Mic ($380) "
                    "+ Neural Stem Cloud Suite ($39/mo) for portable 32-bit field synthesis & stem isolation."
                )

            calc = calculate_cart_pricing_and_tax(selected_items, locale_code, "", "10001", True)
            order_intent_id = gen_stripe_id("aoi_1Q9", 18)
            delegated_token = gen_stripe_id("spt_agent_1Q9", 20)

            agentic_obj = {
                "id": order_intent_id,
                "object": "agentic.order_intent",
                "agent_id": "agt_aetheria_procurement_v2",
                "status": "requires_human_confirmation",
                "delegated_payment_token": {
                    "id": delegated_token,
                    "object": "agentic.delegated_payment_token",
                    "network": "visa_agentic_token_service",
                    "max_amount": calc["total_local"],
                    "currency": calc["profile"]["currency"],
                    "allowed_mcc": ["5733", "5734"],  # Musical Instruments & Computer Software
                    "single_use": True,
                    "expires_at": int(time.time()) + 600,
                    "cryptographic_mandate_hash": hashlib.sha256(f"{order_intent_id}:{calc['total_local']}".encode()).hexdigest()[:32],
                },
                "rationale": rationale,
                "budget_guardrail": {
                    "budget_ceiling_usd_cents": budget_limit_usd_cents,
                    "cart_subtotal_usd_cents": calc["subtotal_usd_cents"],
                    "within_budget": calc["subtotal_usd_cents"] <= budget_limit_usd_cents,
                },
                "recommended_items": selected_items,
                "calculation": calc,
            }

            curl_cmd = (
                f"curl https://api.stripe.com/v1/agentic/order_intents \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
                f"  -d agent_id=agt_aetheria_procurement_v2 \\\n"
                f"  -d 'spending_controls[max_amount]={calc['total_local']}' \\\n"
                f"  -d 'spending_controls[currency]={calc['profile']['currency']}' \\\n"
                f"  -d 'spending_controls[single_use]=true'"
            )
            record_api_log(
                "POST",
                "/v1/agentic/order_intents",
                {
                    "agent_id": "agt_aetheria_procurement_v2",
                    "mandate": mandate,
                    "spending_controls": {
                        "max_amount": calc["total_local"],
                        "currency": calc["profile"]["currency"],
                        "single_use": True,
                    },
                },
                agentic_obj,
                200,
                112,
                curl_cmd,
            )
            emit_webhook_event("agentic.order_intent.created", agentic_obj)
            self._send_json(agentic_obj)
            return

        # 6b. Dedicated Local LLM Chatbot — Step-by-Step Stripe Agentic Commerce Orchestrator (/api/stripe/agentic/chat)
        if path == "/api/stripe/agentic/chat":
            result = execute_agentic_commerce_chat(body)
            http_status = 400 if result.get("status") == "blocked_by_budget_guardrail" and body.get("strict_http_status") else 200
            self._send_json(result, status=http_status)
            return

        # 6c. Human-in-the-Loop Confirmation of a Prepared Agentic OrderIntent (/api/stripe/agentic/confirm_order)
        if path == "/api/stripe/agentic/confirm_order":
            order_intent_id = str(body.get("order_intent_id") or "")
            if order_intent_id not in AGENTIC_ORDERS_STORE:
                self._send_json({"error": {"message": f"Agentic OrderIntent '{order_intent_id}' not found."}}, status=404)
                return
            settlement = confirm_agentic_order_intent(
                order_intent_id,
                use_ollama=bool(body.get("try_ollama", False)),
                original_prompt=str(body.get("prompt") or ""),
            )
            stored = AGENTIC_ORDERS_STORE[order_intent_id]
            self._send_json({
                "status": "succeeded",
                "llm_engine": settlement["llm_engine"],
                "assistant_message": settlement["assistant_message"],
                "order_intent": settlement["order_intent"],
                "delegated_payment_token": stored["delegated_payment_token"],
                "payment_intent": settlement["payment_intent"],
                "calculation": stored["calculation"],
                "steps_5_and_6": settlement["steps_5_and_6"],
            })
            return

        # 7. Stripe Connect v2 Account Onboarding Simulation (/v2/core/accounts)
        if path == "/api/stripe/connect/accounts":
            studio_name = body.get("studio_name", "Nordic Modular Lab AB")
            country = body.get("country", "SE")
            acct_id = gen_stripe_id("acct_2V9", 16)
            acct_obj = {
                "id": acct_id,
                "object": "v2.core.account",
                "display_name": studio_name,
                "contact_email": f"treasury@{studio_name.lower().replace(' ', '')}.io",
                "identity": {"country": country, "entity_type": "company"},
                "configuration": {
                    "merchant": {"capabilities": {"card_payments": {"requested": True}, "transfers": {"requested": True}}},
                    "controller": {
                        "fees": {"payer": "application"},
                        "losses": {"payments": "stripe"},
                        "stripe_dashboard": {"type": "none"},
                    },
                },
                "onboarding_status": "verified_embedded_component",
                "commission_rate_bps": 1200,
            }
            curl_cmd = (
                f"curl https://api.stripe.com/v2/core/accounts \\\n"
                f"  -H 'Authorization: Bearer sk_test_...' \\\n"
                f"  -H 'Stripe-Version: {STRIPE_API_VERSION}' \\\n"
                f"  -H 'Content-Type: application/json' \\\n"
                f"  -d '{{\"display_name\":\"{studio_name}\",\"identity\":{{\"country\":\"{country}\"}}}}'"
            )
            record_api_log(
                "POST",
                "/v2/core/accounts",
                {"display_name": studio_name, "country": country, "controller": acct_obj["configuration"]["controller"]},
                acct_obj,
                200,
                130,
                curl_cmd,
            )
            emit_webhook_event("v2.core.account.created", acct_obj)
            self._send_json(acct_obj)
            return

        # 8. Stripe SetupIntents & Off-Session MIT Vaulting (/v1/setup_intents)
        if path == "/api/stripe/setup_intents":
            usage = body.get("usage", "off_session")
            pm_type = body.get("payment_method_type", "card")
            seti_id = gen_stripe_id("seti_1Q9", 18)
            pm_id = gen_stripe_id("pm_1Q9Vaulted", 16)
            seti_obj = {
                "id": seti_id,
                "object": "setup_intent",
                "customer": "cus_Q9AetheriaDemoStudio",
                "payment_method": pm_id,
                "payment_method_types": [pm_type, "link", "us_bank_account", "sepa_debit"],
                "status": "succeeded",
                "usage": usage,
                "mandate": gen_stripe_id("mandate_1Q9", 16),
                "network_tokenization": {
                    "network_token_id": gen_stripe_id("ntok_vts", 14),
                    "card_account_updater": "enabled_auto_refresh",
                    "mit_exemption": "recurring_or_unscheduled_credential_on_file",
                },
            }
            curl_cmd = (
                f"curl https://api.stripe.com/v1/setup_intents \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -d customer=cus_Q9AetheriaDemoStudio \\\n"
                f"  -d usage={usage} \\\n"
                f"  -d confirm=true"
            )
            record_api_log("POST", "/v1/setup_intents", {"customer": "cus_Q9AetheriaDemoStudio", "usage": usage}, seti_obj, 200, 79, curl_cmd)
            emit_webhook_event("setup_intent.succeeded", seti_obj)
            self._send_json(seti_obj)
            return

        # 9. Stripe Issuing & Treasury Virtual Commercial Cards (/v1/issuing/cards)
        if path == "/api/stripe/issuing/cards":
            cardholder_name = body.get("cardholder_name", "Aetheria Touring Sound Engineer")
            spend_limit_cents = int(body.get("spend_limit_cents", 250000))
            ic_id = gen_stripe_id("ic_1Q9", 18)
            iauth_id = gen_stripe_id("iauth_1Q9", 18)
            card_obj = {
                "id": ic_id,
                "object": "issuing.card",
                "brand": "Visa Commercial",
                "type": "virtual",
                "status": "active",
                "currency": "usd",
                "last4": str(random.randint(1000, 9999)),
                "exp_month": 12,
                "exp_year": 2029,
                "cardholder": {"id": gen_stripe_id("ich_1Q9", 14), "name": cardholder_name},
                "treasury_financial_account": "fa_1Q9AetheriaTreasuryUSD",
                "spending_controls": {
                    "spending_limits": [{"amount": spend_limit_cents, "interval": "per_authorization"}],
                    "allowed_categories": ["musical_instrument_stores", "computer_software_stores", "electronics_stores"],
                },
                "simulated_realtime_authorization": {
                    "id": iauth_id,
                    "object": "issuing.authorization",
                    "approved": True,
                    "amount": 84900,
                    "merchant_data": {"name": "AETHERIA LABS STORE", "mcc": "5733"},
                    "webhook_response_sla_ms": 142,
                },
            }
            curl_cmd = (
                f"curl https://api.stripe.com/v1/issuing/cards \\\n"
                f"  -u sk_test_...: \\\n"
                f"  -d type=virtual -d currency=usd \\\n"
                f"  -d 'spending_controls[spending_limits][0][amount]={spend_limit_cents}' \\\n"
                f"  -d 'spending_controls[spending_limits][0][interval]=per_authorization'"
            )
            record_api_log("POST", "/v1/issuing/cards", {"type": "virtual", "spend_limit_cents": spend_limit_cents}, card_obj, 200, 105, curl_cmd)
            emit_webhook_event("issuing_card.created", card_obj)
            emit_webhook_event("issuing_authorization.request", card_obj["simulated_realtime_authorization"])
            self._send_json(card_obj)
            return

        # 10. Stripe + Bridge Stablecoin Orchestration API (/v0/liquidation_addresses & /v0/transfers)
        if path == "/api/stripe/bridge/orchestrate":
            operation = body.get("operation", "create_liquidation_address")
            chain = body.get("chain", "base").lower()
            asset = body.get("asset", "usdc").lower()
            destination_type = body.get("destination_type", "stripe_fiat_usd")
            amount_usd = float(body.get("amount_usd", 1250.0))

            if chain == "solana":
                onchain_addr = f"Brdg{gen_stripe_id('Sol', 28).replace('_', '')}"
            elif chain == "stellar":
                onchain_addr = f"GBRDG{gen_stripe_id('STLR', 28).replace('_', '').upper()}"
            else:
                onchain_addr = f"0x8F4e{hashlib.sha256(f'{chain}:{asset}:{time.time()}'.encode()).hexdigest()[:36]}"

            if operation == "cross_border_payout":
                tr_id = gen_stripe_id("br_tr_1Q9", 18)
                payout_obj = {
                    "id": tr_id,
                    "object": "bridge.transfer",
                    "orchestrator": "Bridge (a Stripe company)",
                    "state": "payment_processed",
                    "amount": f"{amount_usd:.2f}",
                    "source": {
                        "payment_rail": "stripe_balance",
                        "currency": "usd",
                    },
                    "destination": {
                        "payment_rail": chain,
                        "currency": asset,
                        "to_address": onchain_addr,
                        "recipient_studio": body.get("recipient_name", "Kyoto Acoustics KK (JP)"),
                    },
                    "receipt": {
                        "initial_amount": f"{amount_usd:.2f} USD",
                        "developer_fee": f"{round(amount_usd * 0.005, 2):.2f} USD (50 bps)",
                        "final_amount": f"{round(amount_usd * 0.995, 2):.2f} {asset.upper()}",
                        "tx_hash": f"0x{hashlib.sha256(tr_id.encode()).hexdigest()[:48]}",
                        "settlement_latency_ms": 480 if chain == "solana" else 1720,
                    },
                }
                curl_cmd = (
                    f"curl https://api.bridge.xyz/v0/transfers \\\n"
                    f"  -H 'Api-Key: br_live_...' \\\n"
                    f"  -H 'Idempotency-Key: {gen_stripe_id('idem_br', 12)}' \\\n"
                    f"  -d amount='{amount_usd:.2f}' \\\n"
                    f"  -d 'source[payment_rail]=stripe_balance' -d 'source[currency]=usd' \\\n"
                    f"  -d 'destination[payment_rail]={chain}' -d 'destination[currency]={asset}' \\\n"
                    f"  -d 'destination[to_address]={onchain_addr}'"
                )
                record_api_log("POST", "/v0/transfers (Bridge API)", body, payout_obj, 200, 96, curl_cmd)
                emit_webhook_event("bridge.transfer.payment_processed", payout_obj)
                self._send_json(payout_obj)
                return

            liq_id = gen_stripe_id("br_liq_1Q9", 18)
            liq_obj = {
                "id": liq_id,
                "object": "bridge.liquidation_address",
                "orchestrator": "Bridge (a Stripe company)",
                "chain": chain,
                "currency": asset,
                "address": onchain_addr,
                "customer_id": "cus_Q9AetheriaDemoStudio",
                "destination_payment_rail": "stripe_fiat_balance" if "fiat" in destination_type else "stripe_stablecoin_financial_account",
                "destination_currency": "usd" if destination_type == "stripe_fiat_usd" else ("eur" if destination_type == "stripe_fiat_eur" else "usdb"),
                "destination_financial_account": "fa_1Q9BridgeUSDBYield" if "usdb" in destination_type else "acct_1Q9StripeMerchantBalance",
                "paymaster_gasless_enabled": True,
                "status": "active_monitoring_onchain",
            }
            curl_cmd = (
                f"curl https://api.bridge.xyz/v0/customers/cus_Q9AetheriaDemoStudio/liquidation_addresses \\\n"
                f"  -H 'Api-Key: br_live_...' \\\n"
                f"  -d chain={chain} -d currency={asset} \\\n"
                f"  -d destination_payment_rail={liq_obj['destination_payment_rail']} \\\n"
                f"  -d destination_currency={liq_obj['destination_currency']}"
            )
            record_api_log("POST", "/v0/liquidation_addresses (Bridge API)", body, liq_obj, 200, 88, curl_cmd)
            emit_webhook_event("bridge.liquidation_address.created", liq_obj)
            self._send_json(liq_obj)
            return

        # 11. Raw-Body Cryptographic Webhook Receiver + Idempotent Async Worker Queue (/api/stripe/webhooks/receive)
        if path == "/api/stripe/webhooks/receive":
            raw_bytes = getattr(self, "_last_raw_body", b"")
            sig_header = self.headers.get("Stripe-Signature", "")
            verification = verify_stripe_webhook_raw_body(raw_bytes, sig_header, WEBHOOK_SECRET, tolerance_sec=300)
            if not verification["verified"]:
                err_out = {
                    "error": {
                        "type": "webhook_signature_verification_error",
                        "code": verification["code"],
                        "message": verification["message"],
                        "verification": verification,
                    }
                }
                record_api_log("POST", "/api/stripe/webhooks/receive [HMAC REJECTED]", {"sig": sig_header[:36]}, err_out, 400, 3, "# Rejected by stripe.Webhook.construct_event(raw_body, sig_header, secret)")
                self._send_json(err_out, status=400)
                return

            evt_id = str(body.get("id") or gen_stripe_id("evt_3Q9", 18))
            evt_type = str(body.get("type") or "payment_intent.succeeded")
            now_ts = int(time.time())

            # BEST PRACTICE #4: Idempotent event_id deduplication (INSERT ... ON CONFLICT DO NOTHING) + <200ms HTTP 200 ACK
            if evt_id in PROCESSED_WEBHOOK_EVENTS:
                dup_resp = {
                    "received": True,
                    "status": "duplicate_ignored",
                    "event_id": evt_id,
                    "event_type": evt_type,
                    "idempotent_deduplication": {
                        "already_processed": True,
                        "first_processed_at": PROCESSED_WEBHOOK_EVENTS[evt_id]["processed_at"],
                        "sql_statement": f"INSERT INTO processed_events (event_id, event_type, created_at) VALUES ('{evt_id}', '{evt_type}', {now_ts}) ON CONFLICT (event_id) DO NOTHING;",
                        "rows_inserted": 0,
                        "action": "Skipped duplicate fulfillment; returned immediate HTTP 200 ACK in 2ms.",
                    },
                    "verification": verification,
                    "ack_latency_ms": 2,
                }
                record_api_log("POST", f"/api/stripe/webhooks/receive [DEDUP: {evt_id}]", {"id": evt_id, "type": evt_type}, dup_resp, 200, 2, f"# Duplicate webhook {evt_id} safely ignored via ON CONFLICT DO NOTHING")
                self._send_json(dup_resp, status=200)
                return

            job_id = gen_stripe_id("job_async_fulfill", 12)
            record_entry = {
                "event_id": evt_id,
                "event_type": evt_type,
                "processed_at": now_ts,
                "worker_job_id": job_id,
                "metadata": body.get("data", {}).get("object", {}).get("metadata", {}),
                "status": "completed_async",
            }
            PROCESSED_WEBHOOK_EVENTS[evt_id] = record_entry
            ASYNC_FULFILLMENT_QUEUE.insert(0, record_entry)

            ack_resp = {
                "received": True,
                "status": "enqueued_async_worker",
                "event_id": evt_id,
                "event_type": evt_type,
                "idempotent_deduplication": {
                    "already_processed": False,
                    "sql_statement": f"INSERT INTO processed_events (event_id, event_type, created_at) VALUES ('{evt_id}', '{evt_type}', {now_ts}) ON CONFLICT (event_id) DO NOTHING;",
                    "rows_inserted": 1,
                    "worker_job_id": job_id,
                    "retry_tolerance_window": "72 hours exponential backoff (out-of-order safe)",
                },
                "verification": verification,
                "ack_latency_ms": 4,
            }
            record_api_log("POST", f"/api/stripe/webhooks/receive [ACK <200ms: {evt_id}]", {"id": evt_id, "type": evt_type}, ack_resp, 200, 4, f"# Verified raw-body HMAC & enqueued async worker {job_id}")
            self._send_json(ack_resp, status=200)
            return

        # 12. Interactive 7-Pillar Production Guardrails & Security Test Suite (/api/stripe/guardrails/test)
        if path == "/api/stripe/guardrails/test":
            test_type = body.get("test_type", "zero_trust_tamper")
            now_ts = int(time.time())

            if test_type == "zero_trust_tamper":
                # Simulate attacker attempting to buy $849 Synthesizer for $0.01 (amount=1)
                canonical = CATALOG_BY_ID["prod_synth_mk2"]
                res_payload = {
                    "guardrail": "1. Zero Trust on Client-Side Amounts",
                    "verdict": "BLOCKED_HTTP_400",
                    "attacker_payload": {"items": [{"id": "prod_synth_mk2", "quantity": 1, "price": 1}], "amount": 1},
                    "server_enforcement": {
                        "http_status": 400,
                        "error_code": "zero_trust_client_amount_rejected",
                        "canonical_sku_id": canonical["id"],
                        "canonical_server_unit_amount_cents": canonical["unit_amount_usd"],
                        "explanation": (
                            f"Rejected client-supplied amount=1 ($0.01). Server looks up '{canonical['id']}' in "
                            f"server-side CATALOG -> {canonical['unit_amount_usd']} integer minor units ($849.00)."
                        ),
                    },
                }
                record_api_log("POST", "/v1/payment_intents [GUARDRAIL #1 TEST]", res_payload["attacker_payload"], res_payload["server_enforcement"], 400, 6, "# Guardrail #1: Client amount rejected")
                self._send_json(res_payload)
                return

            if test_type == "idempotency_replay_and_mismatch":
                order_id = body.get("order_id", "ord_90210_studio")
                attempt_no = int(body.get("attempt_no", 1))
                idem_key = f"pi_create_{order_id}_attempt_{attempt_no}"
                mode = body.get("sub_mode", "safe_replay")
                if mode == "param_mismatch":
                    res_payload = {
                        "guardrail": "2. Deterministic Idempotency-Key (Parameter Mismatch HTTP 400)",
                        "verdict": "REJECTED_HTTP_400_IDEMPOTENCY_ERROR",
                        "idempotency_key": idem_key,
                        "ttl_window": "24 hours (86,400 seconds)",
                        "explanation": (
                            f"Reusing '{idem_key}' with a modified cart payload (e.g., adding a second item) "
                            "triggers Stripe HTTP 400 idempotency_error. Deterministic keys bind strictly to the original request fingerprint."
                        ),
                    }
                    record_api_log("POST", f"/v1/payment_intents [GUARDRAIL #2 MISMATCH: {idem_key}]", {"idempotency_key": idem_key, "modified_params": True}, res_payload, 400, 8, f"# HTTP 400 on modified params with key {idem_key}")
                else:
                    res_payload = {
                        "guardrail": "2. Deterministic Idempotency-Key (Safe Network Retry Replay)",
                        "verdict": "REPLAYED_HTTP_200_ZERO_DOUBLE_CHARGE",
                        "idempotency_key": idem_key,
                        "bad_pattern_avoided": "uuid4() inside retry loop (causes double charge on network drop!)",
                        "good_pattern_enforced": f"f'pi_create_{order_id}_attempt_{attempt_no}'",
                        "ttl_window": "24 hours (86,400 seconds)",
                        "explanation": (
                            f"Client retried after a simulated socket timeout using identical deterministic key '{idem_key}'. "
                            "Stripe returned the cached PaymentIntent snapshot without charging the customer twice."
                        ),
                    }
                    record_api_log("POST", f"/v1/payment_intents [GUARDRAIL #2 REPLAY: {idem_key}]", {"idempotency_key": idem_key}, res_payload, 200, 5, f"# Cached replay for {idem_key}")
                self._send_json(res_payload)
                return

            if test_type == "webhook_raw_body_hmac":
                sub_mode = body.get("sub_mode", "valid_raw")
                sample_raw = b'{"id":"evt_3Q9RawBodyTest01","object":"event","type":"payment_intent.succeeded","data":{"object":{"id":"pi_3Q9Test","amount":84900}}}'
                if sub_mode == "reserialized_json_fail":
                    # Valid signature computed on compact raw_body, but verifier receives re-serialized pretty JSON with extra spaces
                    valid_sig = compute_stripe_signature(sample_raw.decode("utf-8"), WEBHOOK_SECRET, now_ts)
                    mutated_bytes = json.dumps(json.loads(sample_raw.decode("utf-8")), indent=2).encode("utf-8")
                    check = verify_stripe_webhook_raw_body(mutated_bytes, valid_sig, WEBHOOK_SECRET, 300)
                elif sub_mode == "stale_timestamp_replay":
                    stale_ts = now_ts - 640  # 640s old (> 300s tolerance)
                    stale_sig = compute_stripe_signature(sample_raw.decode("utf-8"), WEBHOOK_SECRET, stale_ts)
                    check = verify_stripe_webhook_raw_body(sample_raw, stale_sig, WEBHOOK_SECRET, 300)
                else:
                    valid_sig = compute_stripe_signature(sample_raw.decode("utf-8"), WEBHOOK_SECRET, now_ts)
                    check = verify_stripe_webhook_raw_body(sample_raw, valid_sig, WEBHOOK_SECRET, 300)

                res_payload = {
                    "guardrail": "3. Raw-Body Cryptographic Webhook Verification (Stripe-Signature)",
                    "sub_mode": sub_mode,
                    "verification_result": check,
                    "code_pattern": "event = stripe.Webhook.construct_event(payload=await request.body(), sig_header=request.headers['Stripe-Signature'], secret= endpoint_secret, tolerance=300)",
                }
                record_api_log("POST", f"/api/stripe/webhooks/receive [GUARDRAIL #3: {sub_mode}]", {"sub_mode": sub_mode}, res_payload, 200 if check["verified"] else 400, 4, "# Webhook raw-body HMAC & 300s replay check")
                self._send_json(res_payload)
                return

            if test_type == "webhook_idempotent_async":
                evt_id = body.get("event_id", "evt_3Q9IdempotentWebhook99")
                first_time = evt_id not in PROCESSED_WEBHOOK_EVENTS
                if first_time:
                    job_entry = {
                        "event_id": evt_id,
                        "event_type": "payment_intent.succeeded",
                        "processed_at": now_ts,
                        "worker_job_id": gen_stripe_id("job_celery_bq", 10),
                        "status": "completed_async",
                    }
                    PROCESSED_WEBHOOK_EVENTS[evt_id] = job_entry
                    ASYNC_FULFILLMENT_QUEUE.insert(0, job_entry)
                res_payload = {
                    "guardrail": "4. Idempotent & Asynchronous Webhook Fulfillment",
                    "event_id": evt_id,
                    "was_first_delivery": first_time,
                    "rows_inserted": 1 if first_time else 0,
                    "sql_executed": f"INSERT INTO processed_events (event_id) VALUES ('{evt_id}') ON CONFLICT DO NOTHING;",
                    "http_response_code": 200,
                    "ack_latency_ms": 3,
                    "retry_policy_handled": "Stripe retries for 72h with exponential backoff & out-of-order delivery; duplicate event_id safely no-ops.",
                }
                record_api_log("POST", f"/api/stripe/webhooks/receive [GUARDRAIL #4: {'INSERTED' if first_time else 'DEDUP_NOOP'}]", {"event_id": evt_id}, res_payload, 200, 3, res_payload["sql_executed"])
                self._send_json(res_payload)
                return

            if test_type == "exception_taxonomy":
                err_kind = body.get("error_kind", "card_error_402")
                if err_kind == "card_error_402":
                    res_payload = {
                        "guardrail": "5. Granular Stripe Exception Taxonomy",
                        "exception_class": "stripe.error.CardError",
                        "http_status": 402,
                        "decline_code": "insufficient_funds",
                        "should_auto_retry": False,
                        "idempotency_action": "NEVER auto-retry a 402 CardError! Return user-friendly message to UI; when customer enters a new card, increment attempt_no (pi_create_{order_id}_attempt_2).",
                    }
                else:
                    res_payload = {
                        "guardrail": "5. Granular Stripe Exception Taxonomy",
                        "exception_class": "stripe.error.RateLimitError (429) / stripe.error.APIConnectionError (503)",
                        "http_status": 429,
                        "should_auto_retry": True,
                        "backoff_strategy": "Exponential backoff + full jitter (250ms -> 620ms, stripe.max_network_retries = 2)",
                        "idempotency_action": "ALWAYS reuse the EXACT SAME Idempotency-Key (pi_create_{order_id}_attempt_1) across network/429 retries to prevent double charges.",
                    }
                record_api_log("POST", f"/v1/payment_intents [GUARDRAIL #5: {err_kind}]", {"error_kind": err_kind}, res_payload, 200, 7, f"# Exception taxonomy simulation: {err_kind}")
                self._send_json(res_payload)
                return

            if test_type == "expand_and_cursor_pagination":
                res_payload = {
                    "guardrail": "6. Eliminating N+1 API Calls with expand[] & Cursor Pagination",
                    "naive_n_plus_1_latency_ms": 435,
                    "naive_calls": [
                        "1. GET /v1/payment_intents/pi_3Q9... (145ms)",
                        "2. GET /v1/charges/ch_3Q9... (140ms)",
                        "3. GET /v1/balance_transactions/txn_3Q9... (150ms)",
                    ],
                    "optimized_single_call_latency_ms": 148,
                    "optimized_call": "GET /v1/payment_intents/pi_3Q9...?expand[]=latest_charge.balance_transaction&expand[]=customer",
                    "cursor_pagination_example": "GET /v1/payment_intents?limit=10&starting_after=pi_3Q9LastSeenCursor (or SDK auto_paging_iter())",
                    "hydrated_sample": {
                        "id": "pi_3Q9ExpandedDemo",
                        "amount": 84900,
                        "latest_charge": {
                            "id": "ch_3Q9ExpandedDemo",
                            "balance_transaction": {
                                "id": "txn_3Q9ExpandedDemo",
                                "gross": 84900,
                                "fee": 2492,
                                "net": 82408,
                                "exchange_rate": 0.92,
                            },
                        },
                    },
                }
                record_api_log("GET", "/v1/payment_intents?expand[]=latest_charge.balance_transaction", {"expand": ["latest_charge.balance_transaction"]}, res_payload, 200, 48, "curl -G https://api.stripe.com/v1/payment_intents -u sk_test_...: -d 'expand[]=latest_charge.balance_transaction' -d starting_after=pi_3Q9...")
                self._send_json(res_payload)
                return

            if test_type == "metadata_bigquery_propagation":
                order_id = body.get("order_id", "ord_2026_aetheria_8841")
                meta = {
                    "order_id": order_id,
                    "customer_tier": "enterprise",
                    "erp_cost_center": "IT-01",
                }
                res_payload = {
                    "guardrail": "7. Structured metadata Propagation (Webhooks + BigQuery Data Pipeline)",
                    "metadata_attached": meta,
                    "propagated_objects": ["PaymentIntent", "Charge", "TaxCalculation", "Transfer", "Refund"],
                    "bigquery_join_sql": (
                        "SELECT\n"
                        "  pi.id AS payment_intent_id,\n"
                        "  JSON_VALUE(pi.metadata, '$.order_id') AS order_id,\n"
                        "  JSON_VALUE(pi.metadata, '$.customer_tier') AS customer_tier,\n"
                        "  JSON_VALUE(pi.metadata, '$.erp_cost_center') AS erp_cost_center,\n"
                        "  bt.net / 100.0 AS net_settled_usd\n"
                        "FROM `stripe_data_pipeline.payment_intents` pi\n"
                        "JOIN `stripe_data_pipeline.balance_transactions` bt\n"
                        "  ON bt.source = pi.latest_charge\n"
                        f"WHERE JSON_VALUE(pi.metadata, '$.order_id') = '{order_id}';"
                    ),
                }
                record_api_log("POST", "/v1/payment_intents [GUARDRAIL #7: METADATA]", {"metadata": meta}, res_payload, 200, 12, "# Attached structured metadata for BigQuery zero-lookup join")
                self._send_json(res_payload)
                return

            self._send_json({"error": {"message": f"Unknown guardrail test_type: {test_type}"}}, status=400)
            return

        self._send_json({"error": {"message": f"Unknown API endpoint {path}"}}, status=404)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    # Seed initial webhook event so the developer drawer is immediately populated
    emit_webhook_event(
        "Stripe.platform.initialized",
        {
            "store": "Aetheria Labs — Acoustic & Neural Hardware Flagship",
            "api_version": STRIPE_API_VERSION,
            "enabled_modules": [
                "Optimized Checkout Suite (Payment Element + Express Checkout + Link)",
                "Adaptive Pricing + FX Quotes API + Subscription Stability Buffer",
                "Stripe Tax API (Global VAT / Sales Tax + EU B2B Reverse Charge)",
                "Stripe Radar AI Fraud Engine + EMV 3DS2 Step-Up",
                "Stripe Billing + Metronome Usage Meters (/v1/billing/meter_events)",
                "Stripe Connect Accounts v2 (/v2/core/accounts Split Payouts)",
                "Stripe Agentic Commerce Toolkit (/v1/agentic/order_intents)",
            ],
        },
    )
    with ThreadedHTTPServer(("0.0.0.0", PORT), StripeDemoHandler) as httpd:
        print(f"Aetheria Labs Stripe Demo Store running on http://0.0.0.0:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
