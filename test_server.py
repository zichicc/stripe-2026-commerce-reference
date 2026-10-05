#!/usr/bin/env python3
"""End-to-end integration test suite for Aetheria Labs Stripe 2026 E-Commerce Demo Store."""

import json
import threading
import unittest
import urllib.error
import urllib.request

import server


class StripeDemoStoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = server.ThreadedHTTPServer(("127.0.0.1", 0), server.StripeDemoHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str) -> tuple[int, bytes]:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"{self.base_url}{path}") as resp:
            return resp.status, resp.read()

    def _post_json(self, path: str, payload: dict, extra_headers: dict | None = None) -> tuple[int, dict]:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with opener.open(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def _post_raw_bytes(self, path: str, raw_bytes: bytes, extra_headers: dict | None = None) -> tuple[int, dict]:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=raw_bytes,
            headers=headers,
            method="POST",
        )
        try:
            with opener.open(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_01_static_assets_and_initial_state(self) -> None:
        status, html = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Aetheria // Labs", html)

        status_img, img_bytes = self._get("/images/synth_mk2.jpg")
        self.assertEqual(status_img, 200)
        self.assertGreater(len(img_bytes), 1000)

        status_state, raw_state = self._get("/api/state")
        self.assertEqual(status_state, 200)
        state_data = json.loads(raw_state.decode("utf-8"))
        self.assertEqual(len(state_data["catalog"]), 6)
        self.assertIn("US", state_data["locales"])
        self.assertIn("DE", state_data["locales"])
        self.assertIn("JP", state_data["locales"])

    def test_02_stripe_tax_and_eu_reverse_charge(self) -> None:
        # Standard DE consumer VAT (19%)
        status, de_std = self._post_json(
            "/api/stripe/tax/calculations",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "DE",
                "vat_id": "",
                "postal_code": "10115",
            },
        )
        self.assertEqual(status, 200)
        self.assertFalse(de_std["is_eu_reverse_charge"])
        self.assertGreater(de_std["tax_local"], 0)

        # DE B2B Reverse Charge VAT (0%)
        status_rc, de_rc = self._post_json(
            "/api/stripe/tax/calculations",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "DE",
                "vat_id": "DE811907980",
                "postal_code": "10115",
            },
        )
        self.assertEqual(status_rc, 200)
        self.assertTrue(de_rc["is_eu_reverse_charge"])
        self.assertEqual(de_rc["tax_local"], 0)

    def test_03_payment_intents_radar_3ds2_and_connect_splits(self) -> None:
        # 1. Standard success with Connect marketplace item
        status, res = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [
                    {"id": "prod_synth_mk2", "quantity": 1},
                    {"id": "prod_ambernex_dsp", "quantity": 1},
                ],
                "locale": "US",
                "payment_method_type": "card",
                "test_scenario": "success_standard",
            },
        )
        self.assertEqual(status, 200)
        pi = res["payment_intent"]
        self.assertEqual(pi["status"], "succeeded")
        self.assertEqual(len(pi["connect_transfers"]), 1)
        self.assertEqual(pi["connect_transfers"][0]["destination_account"], "acct_2V9klangwerkBerlin")

        # 2. 3DS2 Step-Up Challenge -> Confirm
        status_3ds, res_3ds = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "DE",
                "payment_method_type": "card",
                "test_scenario": "3ds2_challenge",
            },
        )
        self.assertEqual(status_3ds, 200)
        pi_3ds = res_3ds["payment_intent"]
        self.assertEqual(pi_3ds["status"], "requires_action")

        status_conf, res_conf = self._post_json(
            "/api/stripe/payment_intents/confirm_3ds",
            {"payment_intent_id": pi_3ds["id"], "otp_code": "849201"},
        )
        self.assertEqual(status_conf, 200)
        self.assertEqual(res_conf["payment_intent"]["status"], "succeeded")

        # 3. Radar AI High-Risk Block
        status_blk, res_blk = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "US",
                "payment_method_type": "card",
                "test_scenario": "radar_block",
            },
        )
        self.assertEqual(status_blk, 402)
        self.assertEqual(res_blk["payment_intent"]["radar_evaluation"]["risk_score"], 94)

    def test_04_billing_meters_and_agentic_commerce(self) -> None:
        status_mtr, res_mtr = self._post_json(
            "/api/stripe/billing/meter_events",
            {"value": 2000, "workload": "Unit Test Stem Separation"},
        )
        self.assertEqual(status_mtr, 200)
        self.assertGreater(res_mtr["invoice_preview"]["overage_seconds"], 0)

        status_agt, res_agt = self._post_json(
            "/api/stripe/agentic/order_intents",
            {"mandate": "field_rig_under_1300", "budget_limit_usd_cents": 135000, "locale": "US"},
        )
        self.assertEqual(status_agt, 200)
        self.assertTrue(res_agt["delegated_payment_token"]["id"].startswith("spt_agent_"))

        status_conn, res_conn = self._post_json(
            "/api/stripe/connect/accounts",
            {"studio_name": "Stockholm Synth Lab AB", "country": "SE"},
        )
        self.assertEqual(status_conn, 200)
        self.assertEqual(res_conn["object"], "v2.core.account")

    def test_05_manual_capture_void_and_refund_lifecycle(self) -> None:
        # 1. Create with capture_method=manual -> requires_capture
        status_hold, res_hold = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "US",
                "payment_method_type": "card",
                "capture_method": "manual",
                "setup_future_usage": "off_session",
            },
        )
        self.assertEqual(status_hold, 200)
        pi_hold = res_hold["payment_intent"]
        self.assertEqual(pi_hold["status"], "requires_capture")
        self.assertGreater(pi_hold["amount_capturable"], 0)
        self.assertEqual(pi_hold["amount_received"], 0)

        # 2. Partial Capture -> succeeded
        partial_amt = int(pi_hold["amount"] * 0.75)
        status_cap, res_cap = self._post_json(
            "/api/stripe/payment_intents/capture",
            {"payment_intent_id": pi_hold["id"], "amount_to_capture": partial_amt},
        )
        self.assertEqual(status_cap, 200)
        self.assertEqual(res_cap["payment_intent"]["status"], "succeeded")
        self.assertEqual(res_cap["payment_intent"]["amount_received"], partial_amt)

        # 3. Refund with Connect transfer reversal
        status_ref, res_ref = self._post_json(
            "/api/stripe/refunds",
            {
                "payment_intent_id": pi_hold["id"],
                "amount": partial_amt,
                "reverse_transfer": True,
                "refund_application_fee": True,
            },
        )
        self.assertEqual(status_ref, 200)
        self.assertEqual(res_ref["refund"]["status"], "succeeded")
        self.assertTrue(res_ref["payment_intent"]["refunded"])

        # 4. Create another manual hold and Void (/cancel)
        _, res_hold2 = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "US",
                "capture_method": "manual",
            },
        )
        status_void, res_void = self._post_json(
            "/api/stripe/payment_intents/cancel",
            {"payment_intent_id": res_hold2["payment_intent"]["id"], "cancellation_reason": "requested_by_customer"},
        )
        self.assertEqual(status_void, 200)
        self.assertEqual(res_void["payment_intent"]["status"], "canceled")

    def test_06_state_machine_academy_issuing_and_setup_intents(self) -> None:
        # 1. Step through the interactive state machine sandbox
        _, s1 = self._post_json("/api/stripe/state_machine/step", {"action": "create"})
        pi_id = s1["payment_intent"]["id"]
        self.assertEqual(s1["payment_intent"]["status"], "requires_payment_method")

        _, s2 = self._post_json("/api/stripe/state_machine/step", {"action": "attach_pm", "payment_intent_id": pi_id})
        self.assertEqual(s2["payment_intent"]["status"], "requires_confirmation")

        _, s3 = self._post_json("/api/stripe/state_machine/step", {"action": "require_3ds2", "payment_intent_id": pi_id})
        self.assertEqual(s3["payment_intent"]["status"], "requires_action")

        _, s4 = self._post_json("/api/stripe/state_machine/step", {"action": "async_processing", "payment_intent_id": pi_id})
        self.assertEqual(s4["payment_intent"]["status"], "processing")

        _, s5 = self._post_json("/api/stripe/state_machine/step", {"action": "authorize_hold", "payment_intent_id": pi_id})
        self.assertEqual(s5["payment_intent"]["status"], "requires_capture")

        _, s6 = self._post_json("/api/stripe/state_machine/step", {"action": "capture_succeed", "payment_intent_id": pi_id})
        self.assertEqual(s6["payment_intent"]["status"], "succeeded")

        _, s7 = self._post_json("/api/stripe/state_machine/step", {"action": "dispute_defense", "payment_intent_id": pi_id})
        self.assertEqual(s7["payment_intent"]["dispute"]["status"], "won")

        # 2. SetupIntents (/v1/setup_intents)
        status_seti, res_seti = self._post_json(
            "/api/stripe/setup_intents",
            {"usage": "off_session", "payment_method_type": "card"},
        )
        self.assertEqual(status_seti, 200)
        self.assertEqual(res_seti["status"], "succeeded")
        self.assertIn("network_token_id", res_seti["network_tokenization"])

        # 3. Stripe Issuing Virtual Cards (/v1/issuing/cards)
        status_ic, res_ic = self._post_json(
            "/api/stripe/issuing/cards",
            {"cardholder_name": "Test Acoustic Engineer", "spend_limit_cents": 300000},
        )
        self.assertEqual(status_ic, 200)
        self.assertEqual(res_ic["object"], "issuing.card")
        self.assertTrue(res_ic["simulated_realtime_authorization"]["approved"])

    def test_07_bridge_stablecoin_payment_and_orchestration(self) -> None:
        # 1. Checkout PaymentIntent using Bridge Stablecoin (crypto_bridge)
        status_pi, res_pi = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "US",
                "payment_method_type": "crypto_bridge",
                "bridge_asset": "usdb",
                "bridge_chain": "solana",
                "bridge_settlement_mode": "native_stablecoin_treasury",
            },
        )
        self.assertEqual(status_pi, 200)
        br = res_pi["payment_intent"]["bridge_stablecoin_details"]
        self.assertIsNotNone(br)
        self.assertEqual(br["source_asset"], "USDB")
        self.assertEqual(br["source_chain"], "solana")
        self.assertTrue(br["paymaster_gas_sponsored"])

        # 2. Bridge Liquidation Address (/v0/liquidation_addresses)
        status_liq, res_liq = self._post_json(
            "/api/stripe/bridge/orchestrate",
            {
                "operation": "create_liquidation_address",
                "chain": "base",
                "asset": "usdc",
                "destination_type": "stripe_fiat_usd",
            },
        )
        self.assertEqual(status_liq, 200)
        self.assertEqual(res_liq["object"], "bridge.liquidation_address")
        self.assertEqual(res_liq["destination_currency"], "usd")

        # 3. Bridge Cross-Border Payout (/v0/transfers)
        status_pay, res_pay = self._post_json(
            "/api/stripe/bridge/orchestrate",
            {
                "operation": "cross_border_payout",
                "recipient_name": "Kyoto Acoustics KK (JP)",
                "amount_usd": 1250.0,
                "chain": "solana",
                "asset": "usdc",
            },
        )
        self.assertEqual(status_pay, 200)
        self.assertEqual(res_pay["object"], "bridge.transfer")
        self.assertEqual(res_pay["state"], "payment_processed")

        # 4. State Machine Sandbox Bridge Stablecoin action
        _, sm_create = self._post_json("/api/stripe/state_machine/step", {"action": "create"})
        _, sm_bridge = self._post_json(
            "/api/stripe/state_machine/step",
            {"action": "bridge_stablecoin", "payment_intent_id": sm_create["payment_intent"]["id"]},
        )
        self.assertEqual(sm_bridge["payment_intent"]["status"], "succeeded")
        self.assertIn("bridge_stablecoin_details", sm_bridge["payment_intent"])

    def test_08_production_best_practices_and_security_guardrails(self) -> None:
        # 1. Zero Trust on Client-Side Amounts: Reject client-supplied amount/price with HTTP 400
        status_tamper, res_tamper = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1, "price": 1}],
                "amount": 1,
                "locale": "US",
            },
        )
        self.assertEqual(status_tamper, 400)
        self.assertEqual(res_tamper["error"]["code"], "zero_trust_client_amount_rejected")

        # 2. Deterministic Idempotency-Keys: 24h replay on identical params + HTTP 400 on modified params
        idem_key = "pi_create_ord_unit_test_2026_attempt_1"
        status_first, res_first = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "US",
                "order_id": "ord_unit_test_2026",
                "attempt_no": 1,
                "expand": ["latest_charge.balance_transaction"],
                "metadata": {"order_id": "ord_unit_test_2026", "customer_tier": "enterprise", "erp_cost_center": "IT-01"},
            },
            extra_headers={"Idempotency-Key": idem_key},
        )
        self.assertEqual(status_first, 200)
        self.assertFalse(res_first["idempotent_replay"])
        first_pi_id = res_first["payment_intent"]["id"]

        # 2a. Replay with identical parameters -> HTTP 200 cached response (same PaymentIntent ID)
        status_replay, res_replay = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "US",
                "order_id": "ord_unit_test_2026",
                "attempt_no": 1,
            },
            extra_headers={"Idempotency-Key": idem_key},
        )
        self.assertEqual(status_replay, 200)
        self.assertTrue(res_replay["idempotent_replay"])
        self.assertEqual(res_replay["payment_intent"]["id"], first_pi_id)

        # 2b. Reuse same Idempotency-Key with modified parameters -> HTTP 400 idempotency_error
        status_mismatch, res_mismatch = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 2}],
                "locale": "US",
                "order_id": "ord_unit_test_2026",
                "attempt_no": 1,
            },
            extra_headers={"Idempotency-Key": idem_key},
        )
        self.assertEqual(status_mismatch, 400)
        self.assertEqual(res_mismatch["error"]["type"], "idempotency_error")

        # 3 & 4. Raw-Body Cryptographic Webhook Verification + Idempotent Async Worker Queue
        raw_webhook_bytes = b'{"id":"evt_3Q9UnitWebhook01","object":"event","type":"payment_intent.succeeded","data":{"object":{"id":"pi_3Q9Test","metadata":{"order_id":"ord_unit_test_2026"}}}}'
        valid_sig = server.compute_stripe_signature(raw_webhook_bytes.decode("utf-8"))

        # First webhook delivery -> verified & enqueued (<200ms)
        st_wh1, res_wh1 = self._post_raw_bytes(
            "/api/stripe/webhooks/receive",
            raw_webhook_bytes,
            extra_headers={"Stripe-Signature": valid_sig},
        )
        self.assertEqual(st_wh1, 200)
        self.assertEqual(res_wh1["status"], "enqueued_async_worker")
        self.assertEqual(res_wh1["idempotent_deduplication"]["rows_inserted"], 1)

        # Second duplicate webhook delivery -> idempotent no-op (ON CONFLICT DO NOTHING)
        st_wh2, res_wh2 = self._post_raw_bytes(
            "/api/stripe/webhooks/receive",
            raw_webhook_bytes,
            extra_headers={"Stripe-Signature": valid_sig},
        )
        self.assertEqual(st_wh2, 200)
        self.assertEqual(res_wh2["status"], "duplicate_ignored")
        self.assertEqual(res_wh2["idempotent_deduplication"]["rows_inserted"], 0)

        # Re-serialized JSON dict with extra whitespace -> HTTP 400 hmac_signature_mismatch
        reserialized_bytes = json.dumps(json.loads(raw_webhook_bytes.decode("utf-8")), indent=2).encode("utf-8")
        st_wh_bad, res_wh_bad = self._post_raw_bytes(
            "/api/stripe/webhooks/receive",
            reserialized_bytes,
            extra_headers={"Stripe-Signature": valid_sig},
        )
        self.assertEqual(st_wh_bad, 400)
        self.assertEqual(res_wh_bad["error"]["code"], "hmac_signature_mismatch")

        # 5. Granular Stripe Exception Taxonomy (429 RateLimitError vs 402 CardError)
        st_429, res_429 = self._post_json(
            "/api/stripe/payment_intents",
            {
                "items": [{"id": "prod_synth_mk2", "quantity": 1}],
                "locale": "US",
                "order_id": "ord_429_test",
                "attempt_no": 1,
                "test_scenario": "rate_limit_429",
            },
        )
        self.assertEqual(st_429, 429)
        self.assertTrue(res_429["error"]["exception_taxonomy"]["should_auto_retry"])

        # 6 & 7. Eliminating N+1 Calls with expand[] & Cursor Pagination + Structured metadata
        self.assertEqual(res_first["payment_intent"]["metadata"]["erp_cost_center"], "IT-01")
        self.assertIsInstance(res_first["payment_intent"]["latest_charge"], dict)
        self.assertIn("balance_transaction", res_first["payment_intent"]["latest_charge"])

        st_list, raw_list = self._get(
            "/api/stripe/payment_intents?limit=2&expand[]=latest_charge.balance_transaction&expand[]=customer"
        )
        self.assertEqual(st_list, 200)
        list_data = json.loads(raw_list.decode("utf-8"))
        self.assertEqual(list_data["object"], "list")
        self.assertTrue(list_data["single_http_roundtrip"])
        self.assertGreaterEqual(len(list_data["data"]), 1)
        self.assertIn("balance_transaction", list_data["data"][0]["latest_charge"])

    def test_09_agentic_commerce_local_llm_chatbot_flow(self) -> None:
        # 1. Autonomous 6-step Agentic Commerce Chatbot purchase with Bridge USDC on Base
        st_chat, res_chat = self._post_json(
            "/api/stripe/agentic/chat",
            {
                "message": "Buy me a Field Synthesizer MK-II and a Kyoto Binaural Mic under $1,400 using USDC on Base",
                "locale": "US",
                "execution_mode": "auto_complete",
            },
        )
        self.assertEqual(st_chat, 200)
        self.assertEqual(res_chat["status"], "succeeded")
        self.assertEqual(len(res_chat["steps"]), 6)
        self.assertTrue(res_chat["delegated_payment_token"]["id"].startswith("spt_agent_"))
        self.assertTrue(res_chat["delegated_payment_token"]["single_use"])
        self.assertEqual(res_chat["payment_intent"]["status"], "succeeded")
        self.assertIsNotNone(res_chat["payment_intent"]["bridge_stablecoin_details"])
        self.assertEqual(res_chat["payment_intent"]["bridge_stablecoin_details"]["source_chain"], "base")
        self.assertIn("balance_transaction", res_chat["payment_intent"]["latest_charge"])

        # 2. Human-in-the-Loop mode (requires_human_confirmation -> confirm_order -> succeeded)
        st_hil, res_hil = self._post_json(
            "/api/stripe/agentic/chat",
            {
                "message": "Order the AmberNex Euro-DSP unit for our Berlin studio with DE811907980 VAT reverse charge",
                "locale": "DE",
                "execution_mode": "human_in_the_loop",
            },
        )
        self.assertEqual(st_hil, 200)
        self.assertEqual(res_hil["status"], "requires_human_confirmation")
        self.assertIsNone(res_hil["payment_intent"])
        self.assertTrue(res_hil["calculation"]["is_eu_reverse_charge"])
        oi_id = res_hil["order_intent"]["id"]

        st_conf, res_conf = self._post_json(
            "/api/stripe/agentic/confirm_order",
            {"order_intent_id": oi_id},
        )
        self.assertEqual(st_conf, 200)
        self.assertEqual(res_conf["status"], "succeeded")
        self.assertEqual(res_conf["payment_intent"]["status"], "succeeded")

        # 3. Spend Mandate Guardrail Block (Cart exceeds budget ceiling)
        st_blk, res_blk = self._post_json(
            "/api/stripe/agentic/chat",
            {
                "message": "Buy the Field Synthesizer MK-II and Monolith Console with a $500 budget limit",
                "locale": "US",
                "execution_mode": "auto_complete",
            },
        )
        self.assertEqual(st_blk, 200)
        self.assertEqual(res_blk["status"], "blocked_by_budget_guardrail")
        self.assertIsNone(res_blk["delegated_payment_token"])
        self.assertIsNone(res_blk["payment_intent"])


if __name__ == "__main__":
    unittest.main()



