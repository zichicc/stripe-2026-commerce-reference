/**
 * Aetheria Labs — Stripe 2026 E-Commerce Reference Store Frontend Controller
 * Orchestrates:
 *   1. Adaptive Pricing & Regional Payment Method Auto-Ordering
 *   2. Optimized Checkout Suite (Payment Element, Express Checkout, Link, Address Element)
 *   3. Stripe Tax API (/v1/tax/calculations) & EU B2B Reverse Charge VAT Validation
 *   4. Stripe Radar AI Risk Evaluation & EMV 3DS2 Step-Up Challenge Modal
 *   5. Stripe Billing + Metronome Usage Meters (/v1/billing/meter_events)
 *   6. Stripe Connect Accounts v2 (/v2/core/accounts) & Split Payout Waterfall
 *   7. Stripe Agentic Commerce Toolkit (/v1/agentic/order_intents)
 *   8. Live Developer API & Signed Webhook Event Stream Inspector
 */

const state = {
  config: {},
  catalog: [],
  locales: {},
  currentLocale: 'US',
  activeFilter: 'all',
  activeView: 'storefront',
  selectedPaymentMethod: 'card',
  selectedScenario: 'success_standard',
  bridgeAsset: 'usdc',
  bridgeChain: 'base',
  bridgeSettlementMode: 'auto_fiat_liquidation',
  pending3DSPaymentIntentId: null,
  latestPaymentIntent: null,
  currentSmStep: 0,
  smCodeLang: 'curl',
  smSandboxIntent: null,
  cart: [
    { id: 'prod_synth_mk2', quantity: 1 },
    { id: 'prod_ambernex_dsp', quantity: 1 },
  ],
  latestTaxCalculation: null,
  meterUsage: null,
  webhookEvents: [],
  apiLogs: [],
  selectedInspectorItemId: null,
  agenticStepsTrace: [],
  selectedAgenticStepIndex: 0,
};

// Format minor units (cents or zero-decimal JPY) using locale profile
function formatLocalMoney(usdCents, localeCode = state.currentLocale) {
  const profile = state.locales[localeCode];
  if (!profile) return `$${(usdCents / 100).toFixed(2)}`;
  const rate = profile.fx_rate;
  if (profile.zero_decimal) {
    const val = Math.round((usdCents / 100) * rate);
    return `${profile.symbol}${val.toLocaleString('en-US')}`;
  }
  const val = (usdCents * rate) / 100;
  return `${profile.symbol}${val.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatMinorUnitsDirect(minorAmount, localeCode = state.currentLocale) {
  const profile = state.locales[localeCode];
  if (!profile) return `$${(minorAmount / 100).toFixed(2)}`;
  if (profile.zero_decimal) {
    return `${profile.symbol}${Math.round(minorAmount).toLocaleString('en-US')}`;
  }
  return `${profile.symbol}${(minorAmount / 100).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

async function fetchJson(url, options = {}) {
  const mergedHeaders = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  const resp = await fetch(url, {
    ...options,
    headers: mergedHeaders,
  });
  const data = await resp.json();
  return { status: resp.status, data };
}

function updateLiveIdempotencyPreview() {
  const orderEl = document.getElementById('input-order-id');
  const attemptEl = document.getElementById('input-attempt-no');
  const previewEl = document.getElementById('live-idem-key-preview');
  if (orderEl && attemptEl && previewEl) {
    previewEl.textContent = `pi_create_${orderEl.value.trim() || 'ord_default'}_attempt_${attemptEl.value || 1}`;
  }
}

// ==========================================================================
// INITIALIZATION & STATE SYNC
// ==========================================================================

async function initApp() {
  const { data } = await fetchJson('/api/state');
  state.config = data.config;
  state.catalog = data.catalog;
  state.locales = data.locales;
  state.meterUsage = data.meter_usage;
  state.webhookEvents = data.webhook_events || [];
  state.apiLogs = data.api_logs || [];

  bindNavigationAndControls();
  updateLiveIdempotencyPreview();
  renderAdaptivePricingTelemetry();
  renderCatalog();
  renderCheckoutPaymentMethods();
  renderBillingMeterView();
  renderStateMachineAcademy();
  renderAgenticStepsPipeline();
  renderDeveloperInspector();
  await recalculateCartAndTax();
}

async function refreshTelemetryStreams() {
  const { data } = await fetchJson('/api/stripe/webhooks');
  state.webhookEvents = data.events || [];
  state.apiLogs = data.api_logs || [];
  renderDeveloperInspector();
}

// ==========================================================================
// NAVIGATION & GLOBAL CONTROLS
// ==========================================================================

function switchView(viewName) {
  if (viewName === 'agentic-chat') {
    window.toggleAgenticPopup(true);
    return;
  }
  state.activeView = viewName;
  document.querySelectorAll('.nav-tab').forEach((btn) => {
    if (btn.dataset.view === 'agentic-chat') return;
    btn.classList.toggle('is-active', btn.dataset.view === viewName);
  });
  document.querySelectorAll('.view-panel').forEach((panel) => {
    panel.classList.toggle('is-active', panel.id === `view-${viewName}`);
  });
  if (viewName === 'checkout') {
    recalculateCartAndTax();
  } else if (viewName === 'statemachine') {
    renderStateMachineAcademy();
  }
}

function bindNavigationAndControls() {
  // Primary tabs
  document.querySelectorAll('.nav-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (btn.dataset.view === 'agentic-chat') {
        window.toggleAgenticPopup();
      } else {
        switchView(btn.dataset.view);
      }
    });
  });

  // Hero & header shortcuts
  document.getElementById('btn-header-checkout').addEventListener('click', () => switchView('checkout'));
  document.getElementById('btn-hero-go-checkout').addEventListener('click', () => switchView('checkout'));
  const btnHeroAgentic = document.getElementById('btn-hero-go-agentic');
  if (btnHeroAgentic) {
    btnHeroAgentic.addEventListener('click', () => switchView('agentic'));
  }
  document.getElementById('btn-hero-go-statemachine').addEventListener('click', () => switchView('statemachine'));
  const btnHeroAgenticChat = document.getElementById('btn-hero-go-agentic-chat');
  if (btnHeroAgenticChat) {
    btnHeroAgenticChat.addEventListener('click', () => window.toggleAgenticPopup(true));
  }
  const btnHeroGuardrails = document.getElementById('btn-hero-go-guardrails');
  if (btnHeroGuardrails) {
    btnHeroGuardrails.addEventListener('click', () => switchView('guardrails'));
  }
  document.getElementById('btn-checkout-open-sm-lab').addEventListener('click', () => switchView('statemachine'));

  // Deterministic Idempotency-Key controls in Checkout
  const orderInput = document.getElementById('input-order-id');
  const attemptInput = document.getElementById('input-attempt-no');
  if (orderInput && attemptInput) {
    orderInput.addEventListener('input', updateLiveIdempotencyPreview);
    attemptInput.addEventListener('input', updateLiveIdempotencyPreview);
    document.getElementById('btn-new-order-id').addEventListener('click', () => {
      orderInput.value = `ord_2026_aeth_${Math.floor(100 + Math.random() * 900)}`;
      attemptInput.value = '1';
      updateLiveIdempotencyPreview();
    });
    document.getElementById('btn-inc-attempt').addEventListener('click', () => {
      attemptInput.value = String(Number(attemptInput.value || 1) + 1);
      updateLiveIdempotencyPreview();
    });
    document.getElementById('btn-retry-same-idem-key').addEventListener('click', () => {
      submitCheckoutPaymentIntent(false, '', true);
    });
  }

  // State Machine Prev/Next Step buttons
  document.getElementById('btn-sm-prev-step').addEventListener('click', () => {
    state.currentSmStep = (state.currentSmStep - 1 + STATE_MACHINE_CURRICULUM.length) % STATE_MACHINE_CURRICULUM.length;
    renderStateMachineAcademy();
  });
  document.getElementById('btn-sm-next-step').addEventListener('click', () => {
    state.currentSmStep = (state.currentSmStep + 1) % STATE_MACHINE_CURRICULUM.length;
    renderStateMachineAcademy();
  });

  // Locale / Adaptive Pricing selector
  const localeSelect = document.getElementById('select-locale');
  localeSelect.addEventListener('change', async (e) => {
    state.currentLocale = e.target.value;
    const profile = state.locales[state.currentLocale];
    if (profile && profile.ai_ordered_methods.length > 0) {
      state.selectedPaymentMethod = profile.ai_ordered_methods[0].id;
    }
    const defaultPostals = {
      US: '10001',
      DE: '10115',
      NL: '1012 JS',
      GB: 'EC2A 4NE',
      TR: '34394',
      JP: '150-0001',
    };
    document.getElementById('input-postal-code').value = defaultPostals[state.currentLocale] || '10001';
    document.getElementById('label-country-code').textContent = state.currentLocale;

    renderAdaptivePricingTelemetry();
    renderCatalog();
    renderCheckoutPaymentMethods();
    await recalculateCartAndTax();
  });

  // Category filter pills
  document.querySelectorAll('.filter-pill').forEach((pill) => {
    pill.addEventListener('click', () => {
      state.activeFilter = pill.dataset.filter;
      document.querySelectorAll('.filter-pill').forEach((p) => p.classList.remove('is-active'));
      pill.classList.add('is-active');
      renderCatalog();
    });
  });

  // Tax recalculation & B2B VAT ID test button
  document.getElementById('btn-recalculate-tax').addEventListener('click', () => recalculateCartAndTax());
  document.getElementById('input-postal-code').addEventListener('change', () => recalculateCartAndTax());
  document.getElementById('input-vat-id').addEventListener('change', () => recalculateCartAndTax());
  document.getElementById('btn-fill-sample-vat').addEventListener('click', async () => {
    if (state.currentLocale !== 'DE' && state.currentLocale !== 'NL') {
      state.currentLocale = 'DE';
      document.getElementById('select-locale').value = 'DE';
      document.getElementById('input-postal-code').value = '10115';
      document.getElementById('label-country-code').textContent = 'DE';
      renderAdaptivePricingTelemetry();
      renderCatalog();
      renderCheckoutPaymentMethods();
    }
    document.getElementById('input-vat-id').value = 'DE811907980';
    await recalculateCartAndTax();
  });

  // Radar & 3DS2 scenario chips
  document.querySelectorAll('.scenario-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      state.selectedScenario = chip.dataset.scenario;
      document.querySelectorAll('.scenario-chip').forEach((c) => c.classList.remove('is-active'));
      chip.classList.add('is-active');
    });
  });

  // Submit PaymentIntent button
  document.getElementById('btn-submit-payment').addEventListener('click', () => submitCheckoutPaymentIntent(false));

  // 3DS2 Modal actions
  document.getElementById('btn-confirm-3ds2').addEventListener('click', () => confirm3DS2StepUp());
  document.getElementById('btn-cancel-3ds2').addEventListener('click', () => {
    document.getElementById('modal-3ds2').classList.remove('is-open');
  });

  // Billing Meter Ingestion buttons
  document.getElementById('btn-ingest-meter-small').addEventListener('click', () =>
    ingestMeterEvent(1250, '8-Track Stem Isolation & De-Bleed (96kHz)')
  );
  document.getElementById('btn-ingest-meter-large').addEventListener('click', () =>
    ingestMeterEvent(3000, 'Dolby Atmos 7.1.4 Spatial Master Render')
  );

  // Agentic Commerce, Connect v2, Issuing, SetupIntents & Bridge Stablecoin buttons
  document.getElementById('btn-run-agentic-intent').addEventListener('click', () => runAgenticOrderIntent());
  document.getElementById('btn-create-connect-account').addEventListener('click', () => createConnectV2Account());
  document.getElementById('btn-issue-virtual-card').addEventListener('click', () => issueVirtualCommercialCard());
  document.getElementById('btn-run-setup-intent').addEventListener('click', () => runSetupIntentVaulting());
  document.getElementById('btn-create-bridge-liquidation').addEventListener('click', () => createBridgeLiquidationAddress());
  document.getElementById('btn-run-bridge-payout').addEventListener('click', () => runBridgeCrossBorderPayout());

  // API Configuration Modal
  document.getElementById('btn-open-api-config').addEventListener('click', () => {
    document.getElementById('modal-api-config').classList.add('is-open');
  });
  document.getElementById('btn-close-api-config').addEventListener('click', () => {
    document.getElementById('modal-api-config').classList.remove('is-open');
  });
  document.getElementById('btn-save-api-config').addEventListener('click', () => saveRuntimeApiConfig());

  // Developer Inspector Drawer Toggle
  document.getElementById('dev-inspector-toggle').addEventListener('click', () => {
    const bar = document.getElementById('dev-inspector-bar');
    const expanded = bar.classList.toggle('is-expanded');
    document.getElementById('dev-bar-expand-label').textContent = expanded
      ? '[▼ Collapse Inspector]'
      : '[▲ Expand Inspector]';
  });
}

// ==========================================================================
// 1. ADAPTIVE PRICING & STOREFRONT CATALOG
// ==========================================================================

function renderAdaptivePricingTelemetry() {
  const profile = state.locales[state.currentLocale];
  if (!profile) return;

  document.getElementById('telemetry-fx-summary').textContent =
    `FX Quote: ${profile.fx_rate} ${profile.currency.toUpperCase()} · ${profile.tax_name}`;
  document.getElementById('fx-card-currency').textContent =
    `${profile.currency.toUpperCase()} (${profile.symbol}) · ${profile.fx_rate}x`;
  document.getElementById('fx-card-tax').textContent = profile.tax_name;
  document.getElementById('fx-card-top-pm').textContent =
    profile.ai_ordered_methods[0]?.label.split(' (')[0] || 'Link';
  document.getElementById('fx-card-buffer').textContent =
    profile.stability_buffer_pct > 0
      ? `${profile.stability_buffer_pct.toFixed(1)}% Locked Shield`
      : '0.0% (Base USD)';
  document.getElementById('catalog-currency-label').textContent = profile.currency.toUpperCase();
}

function renderCatalog() {
  const grid = document.getElementById('catalog-grid');
  const filtered = state.catalog.filter(
    (item) => state.activeFilter === 'all' || item.commerce_model === state.activeFilter
  );
  document.getElementById('catalog-visible-count').textContent = String(filtered.length);

  grid.innerHTML = filtered
    .map((item) => {
      const localPrice = formatLocalMoney(item.unit_amount_usd);
      const isSub = item.commerce_model === 'subscription_metered';
      const priceSuffix = isSub ? ' / mo + metered' : '';
      const fxNote =
        state.currentLocale === 'US'
          ? `Base Price · $${(item.unit_amount_usd / 100).toFixed(2)} USD`
          : `Adaptive Pricing from $${(item.unit_amount_usd / 100).toFixed(2)} USD`;

      const sellerHtml = item.seller
        ? `<div class="connect-seller-box">
             <span>Partner: <strong>${item.seller.name}</strong> (${item.seller.country})</span>
             <code>${item.seller.account_id}</code>
           </div>`
        : '';

      return `
        <article class="product-card" id="card-${item.id}">
          <div class="product-card__media">
            <img src="${item.image}" alt="${item.name}" class="product-card__img" loading="lazy" />
            <span class="product-card__badge">${item.badge}</span>
            <span class="product-card__tax-tag">${item.tax_code_label}</span>
          </div>
          <div class="product-card__body">
            <div class="product-card__category">${item.category}</div>
            <h2 class="product-card__title">${item.name}</h2>
            <p class="product-card__subtitle">${item.subtitle}</p>
            <div class="product-card__specs">
              ${item.specs.map((s) => `<span class="spec-chip">${s}</span>`).join('')}
            </div>
            ${sellerHtml}
            <div class="stripe-pill-row">
              ${item.stripe_features.map((f) => `<span class="stripe-feature-pill">${f}</span>`).join('')}
            </div>
            <div class="product-card__footer">
              <div class="price-block">
                <span class="price-block__current">${localPrice}${priceSuffix}</span>
                <span class="price-block__fx-note">${fxNote}</span>
              </div>
              <div style="display: flex; gap: 0.45rem;">
                <button type="button" class="btn" onclick="addToCart('${item.id}', false)">
                  + Cart
                </button>
                <button type="button" class="btn btn--primary" onclick="addToCart('${item.id}', true)">
                  Buy Now
                </button>
              </div>
            </div>
          </div>
        </article>
      `;
    })
    .join('');
}

window.addToCart = async function (productId, goToCheckout = false) {
  const existing = state.cart.find((c) => c.id === productId);
  if (existing) {
    existing.quantity += 1;
  } else {
    state.cart.push({ id: productId, quantity: 1 });
  }
  updateCartBadges();
  await recalculateCartAndTax();
  if (goToCheckout) {
    switchView('checkout');
  }
};

window.changeCartQty = async function (productId, delta) {
  const idx = state.cart.findIndex((c) => c.id === productId);
  if (idx === -1) return;
  state.cart[idx].quantity += delta;
  if (state.cart[idx].quantity <= 0) {
    state.cart.splice(idx, 1);
  }
  updateCartBadges();
  await recalculateCartAndTax();
};

function updateCartBadges() {
  const totalQty = state.cart.reduce((acc, item) => acc + item.quantity, 0);
  document.getElementById('header-cart-count').textContent = String(totalQty);
  document.getElementById('nav-checkout-badge').textContent = String(totalQty);
}

// ==========================================================================
// 2. OPTIMIZED CHECKOUT SUITE (OCS) & STRIPE TAX CALCULATION
// ==========================================================================

function renderCheckoutPaymentMethods() {
  const profile = state.locales[state.currentLocale];
  if (!profile) return;

  document.getElementById('pm-locale-indicator').textContent =
    `Market: ${profile.country} (${profile.currency.toUpperCase()})`;

  // 1. Express Checkout Element wallets
  const walletsContainer = document.getElementById('express-wallets-container');
  walletsContainer.innerHTML = profile.express_wallets
    .map((walletName, idx) => {
      let cls = 'wallet-btn--secondary';
      if (walletName.includes('Link')) cls = 'wallet-btn--link';
      else if (walletName.includes('Apple')) cls = 'wallet-btn--apple';
      else if (walletName.includes('Google')) cls = 'wallet-btn--google';
      return `
        <button type="button" class="wallet-btn ${cls}" id="express-wallet-btn-${idx}" onclick="triggerExpressWalletCheckout('${walletName}')">
          <span>⚡ ${walletName}</span>
        </button>
      `;
    })
    .join('');

  // 2. AI-Ordered Payment Element Tabs
  const tabsContainer = document.getElementById('payment-methods-tabs');
  tabsContainer.innerHTML = profile.ai_ordered_methods
    .map((pm) => {
      const selected = pm.id === state.selectedPaymentMethod ? 'is-selected' : '';
      return `
        <button type="button" class="pm-tab ${selected}" onclick="selectPaymentMethodTab('${pm.id}')">
          <span class="pm-tab__title">${pm.label}</span>
          <span class="pm-tab__badge">${pm.badge}</span>
        </button>
      `;
    })
    .join('');

  renderSelectedPaymentMethodSurface();
}

window.selectPaymentMethodTab = function (pmId) {
  state.selectedPaymentMethod = pmId;
  renderCheckoutPaymentMethods();
};

function renderSelectedPaymentMethodSurface() {
  const container = document.getElementById('payment-element-dynamic-body');
  const pmId = state.selectedPaymentMethod;

  if (pmId === 'card') {
    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.55rem;">
        <strong style="font-size: 0.82rem;">Stripe Payment Element · Network Tokenized Card</strong>
        <span style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--accent-cobalt);">Visa / MC / Amex / JCB</span>
      </div>
      <div class="field-grid">
        <div class="field-group field-group--full">
          <label class="field-label">Card Number (Managed by Radar Test Scenario below)</label>
          <input type="text" class="field-input" value="4242 •••• •••• 4242" readonly style="font-family: var(--font-mono); background: var(--bg-surface);" />
        </div>
        <div class="field-group">
          <label class="field-label">Expiration</label>
          <input type="text" class="field-input" value="08 / 29" readonly style="font-family: var(--font-mono);" />
        </div>
        <div class="field-group">
          <label class="field-label">CVC &amp; Network Cryptogram</label>
          <input type="text" class="field-input" value="842 (ECI-05 Token)" readonly style="font-family: var(--font-mono);" />
        </div>
      </div>
    `;
  } else if (pmId === 'us_bank_account' || pmId === 'sepa_debit' || pmId === 'pay_by_bank' || pmId === 'ideal' || pmId === 'bancontact') {
    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem;">
        <strong style="font-size: 0.82rem;">Stripe Financial Connections / Instant Bank Transfer</strong>
        <span style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--accent-link-green);">Instant Balance Verified</span>
      </div>
      <p style="font-size: 0.8rem; color: var(--ink-secondary); margin-bottom: 0.5rem;">
        Connected Institution: <strong>Mercury / Deutsche Bank Treasury (•••• 9042)</strong> · Real-time account ownership &amp; balance check completed via <code>financial_connections.session</code>.
      </p>
    `;
  } else if (pmId === 'crypto_bridge' || pmId === 'crypto_usdc' || pmId === 'crypto') {
    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
        <div>
          <strong style="font-size: 0.85rem;">Stripe + Bridge Stablecoin Checkout (<code>payment_method_types: ["crypto"]</code>)</strong>
          <div style="font-size: 0.74rem; color: var(--ink-secondary);">
            Orchestrated via Bridge <code>/v0/liquidation_addresses</code> · ERC-4337 Paymaster Gasless Sponsorship
          </div>
        </div>
        <span class="surface-panel__tag" style="background: rgba(99, 91, 255, 0.12); color: var(--accent-cobalt);">
          Bridge v0 · 0.5% Fee · 0% Chargeback
        </span>
      </div>
      <div class="field-grid" style="margin-bottom: 0.65rem;">
        <div class="field-group">
          <label class="field-label" for="select-bridge-asset">Stablecoin Asset</label>
          <select id="select-bridge-asset" class="field-select" onchange="state.bridgeAsset = this.value">
            <option value="usdc" ${state.bridgeAsset === 'usdc' ? 'selected' : ''}>USDC (Circle USD Coin · 1:1 Peg)</option>
            <option value="usdb" ${state.bridgeAsset === 'usdb' ? 'selected' : ''}>USDB (Bridge Yield-Bearing Stablecoin)</option>
            <option value="eurc" ${state.bridgeAsset === 'eurc' ? 'selected' : ''}>EURC (Circle Euro Coin · MiCA)</option>
            <option value="pyusd" ${state.bridgeAsset === 'pyusd' ? 'selected' : ''}>PYUSD (PayPal USD)</option>
          </select>
        </div>
        <div class="field-group">
          <label class="field-label" for="select-bridge-chain">Blockchain L1/L2 Network</label>
          <select id="select-bridge-chain" class="field-select" onchange="state.bridgeChain = this.value">
            <option value="base" ${state.bridgeChain === 'base' ? 'selected' : ''}>Base (Coinbase L2 · ~1.5s Finality)</option>
            <option value="solana" ${state.bridgeChain === 'solana' ? 'selected' : ''}>Solana (SPL · 400ms Finality)</option>
            <option value="arbitrum" ${state.bridgeChain === 'arbitrum' ? 'selected' : ''}>Arbitrum One (EVM Rollup L2)</option>
            <option value="polygon" ${state.bridgeChain === 'polygon' ? 'selected' : ''}>Polygon PoS</option>
            <option value="stellar" ${state.bridgeChain === 'stellar' ? 'selected' : ''}>Stellar Network</option>
            <option value="ethereum" ${state.bridgeChain === 'ethereum' ? 'selected' : ''}>Ethereum Mainnet (ERC-20)</option>
          </select>
        </div>
        <div class="field-group field-group--full">
          <label class="field-label" for="select-bridge-settlement">Merchant Settlement Destination (Bridge Liquidation Route)</label>
          <select id="select-bridge-settlement" class="field-select" onchange="state.bridgeSettlementMode = this.value">
            <option value="auto_fiat_liquidation" ${state.bridgeSettlementMode === 'auto_fiat_liquidation' ? 'selected' : ''}>
              Auto-Liquidate to Local Fiat in Stripe Balance (USD/EUR/GBP · Zero FX Slippage)
            </option>
            <option value="native_stablecoin_treasury" ${state.bridgeSettlementMode === 'native_stablecoin_treasury' ? 'selected' : ''}>
              Hold Native USDB / USDC in Stripe Stablecoin Financial Account (fa_1Q9BridgeUSDBYield)
            </option>
          </select>
        </div>
      </div>
      <div style="padding: 0.55rem 0.75rem; background: var(--bg-surface); border: 1px solid var(--border-hairline); border-radius: 6px; font-family: var(--font-mono); font-size: 0.72rem; color: var(--ink-secondary);">
        <div>✓ <strong>Connected Passkey Wallet:</strong> <code>0x71C...9A4B</code> (EIP-712 Permit2 Gasless Signature Ready)</div>
        <div>✓ <strong>Bridge Liquidation Route:</strong> Incoming ${state.bridgeAsset.toUpperCase()} on <code>${state.bridgeChain}</code> settles instantaneously to merchant balance.</div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem;">
        <strong style="font-size: 0.82rem;">Accelerated Wallet / Buy Now, Pay Later (${pmId.toUpperCase()})</strong>
        <span style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--accent-link-green);">Pre-Qualified</span>
      </div>
      <p style="font-size: 0.8rem; color: var(--ink-secondary);">
        Stripe dynamically surfaces <strong>${pmId.toUpperCase()}</strong> based on cart value, product category, and customer IP locale, settling 100% upfront to Aetheria Labs.
      </p>
    `;
  }
}

async function recalculateCartAndTax() {
  const vatId = document.getElementById('input-vat-id').value.trim();
  const postalCode = document.getElementById('input-postal-code').value.trim() || '10001';

  const { data } = await fetchJson('/api/stripe/tax/calculations', {
    method: 'POST',
    body: JSON.stringify({
      items: state.cart,
      locale: state.currentLocale,
      vat_id: vatId,
      postal_code: postalCode,
      apply_stability_buffer: true,
    }),
  });

  state.latestTaxCalculation = data;
  renderCheckoutSummaryAndSplits(data);
  await refreshTelemetryStreams();
}

function renderCheckoutSummaryAndSplits(calcData) {
  const listEl = document.getElementById('checkout-cart-list');
  const lineItems = calcData.tax_calculation?.line_items || [];

  if (lineItems.length === 0) {
    listEl.innerHTML = `<div style="padding: 1rem; color: var(--ink-muted); font-size: 0.85rem;">Your cart is empty. Add products from the Flagship Storefront.</div>`;
  } else {
    listEl.innerHTML = lineItems
      .map((li) => {
        const prod = state.catalog.find((p) => p.id === li.product_id);
        const imgUrl = prod ? prod.image : '/images/synth_mk2.jpg';
        return `
          <div class="cart-line-item">
            <div class="cart-line-item__info">
              <img src="${imgUrl}" alt="${li.name}" class="cart-line-item__thumb" />
              <div>
                <div class="cart-line-item__title">${li.name}</div>
                <div class="cart-line-item__meta">
                  <code>${li.tax_code}</code> · Tax: ${li.tax_rate_pct}% (${li.taxability_reason})
                </div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <div class="qty-controls">
                <button type="button" class="qty-btn" onclick="changeCartQty('${li.product_id}', -1)">-</button>
                <span style="font-family: var(--font-mono); font-size: 0.78rem;">${li.quantity}</span>
                <button type="button" class="qty-btn" onclick="changeCartQty('${li.product_id}', 1)">+</button>
              </div>
              <strong style="font-family: var(--font-mono); font-size: 0.86rem; min-width: 75px; text-align: right;">
                ${formatMinorUnitsDirect(li.amount)}
              </strong>
            </div>
          </div>
        `;
      })
      .join('');
  }

  // Update Ledger
  const totalItems = lineItems.reduce((acc, li) => acc + li.quantity, 0);
  document.getElementById('ledger-item-count').textContent = String(totalItems);
  document.getElementById('ledger-subtotal').textContent = calcData.formatted.subtotal;
  document.getElementById('ledger-shipping').textContent = calcData.formatted.shipping;

  const taxLabel = calcData.is_eu_reverse_charge
    ? `Stripe Tax (0% EU B2B Reverse Charge · VAT Verified)`
    : `Stripe Tax (${calcData.profile.tax_name})`;
  document.getElementById('ledger-tax-label').textContent = taxLabel;
  document.getElementById('ledger-tax').textContent = calcData.formatted.tax;

  const bufferRow = document.getElementById('ledger-buffer-row');
  if (calcData.has_subscription && calcData.profile.stability_buffer_pct > 0) {
    bufferRow.style.display = 'flex';
    document.getElementById('ledger-buffer-val').textContent =
      `Active (${calcData.profile.stability_buffer_pct}% Renewal Shield)`;
  } else {
    bufferRow.style.display = 'none';
  }

  document.getElementById('ledger-currency-code').textContent = calcData.profile.currency.toUpperCase();
  document.getElementById('ledger-total').textContent = calcData.formatted.total;
  document.getElementById('btn-pay-amount').textContent = calcData.formatted.total;
  document.getElementById('fx-card-quote-id').textContent = calcData.fx_quote.id;

  // Render Stripe Connect v2 Multi-Vendor Split Waterfall
  const waterfallContainer = document.getElementById('connect-waterfall-items');
  if (!calcData.connect_transfers || calcData.connect_transfers.length === 0) {
    waterfallContainer.innerHTML = `
      <div class="split-item" style="color: var(--ink-muted);">
        No third-party Connect marketplace items in cart. Add <strong>AmberNex Euro-DSP</strong> or <strong>Kyoto Binaural Mic</strong> to inspect automated <code>/v2/core/accounts</code> split transfers.
      </div>
    `;
  } else {
    waterfallContainer.innerHTML = calcData.connect_transfers
      .map(
        (tr) => `
          <div class="split-item">
            <div class="ledger-row">
              <strong>${tr.seller_name} (${tr.seller_country})</strong>
              <code>${tr.destination_account}</code>
            </div>
            <div class="ledger-row" style="margin-top: 0.25rem; color: var(--ink-secondary);">
              <span>Gross Item Share: ${formatMinorUnitsDirect(tr.gross_amount)}</span>
              <span>Platform Fee (12%): -${formatMinorUnitsDirect(tr.application_fee_amount)}</span>
            </div>
            <div class="ledger-row" style="margin-top: 0.15rem; color: var(--accent-link-green); font-weight: 700;">
              <span>transfer_data[destination] Net Payout:</span>
              <span>${formatMinorUnitsDirect(tr.net_transfer_amount)}</span>
            </div>
          </div>
        `
      )
      .join('');
  }
}

// ==========================================================================
// 3. PAYMENT INTENT EXECUTION, EXPRESS WALLETS, RADAR & 3DS2 CHALLENGE
// ==========================================================================

window.triggerExpressWalletCheckout = async function (walletName) {
  if (walletName.toLowerCase().includes('bridge')) {
    state.selectedPaymentMethod = 'crypto_bridge';
  } else {
    state.selectedPaymentMethod = walletName.toLowerCase().replace(/\s+/g, '_');
  }
  await submitCheckoutPaymentIntent(true, walletName);
};

async function submitCheckoutPaymentIntent(isExpress = false, expressLabel = '', forceSameKeyReplay = false) {
  const feedbackEl = document.getElementById('checkout-feedback-banner');
  feedbackEl.innerHTML = '';

  if (state.cart.length === 0) {
    feedbackEl.innerHTML = `<div class="alert-banner alert-banner--error">Your cart is empty. Add at least one product before creating a PaymentIntent.</div>`;
    return;
  }

  const vatId = document.getElementById('input-vat-id').value.trim();
  const postalCode = document.getElementById('input-postal-code').value.trim() || '10001';
  const email = document.getElementById('input-customer-email').value.trim();
  const captureMethod = document.getElementById('select-capture-method').value || 'automatic';
  const setupFutureUsage = document.getElementById('select-setup-future-usage').value || null;
  const orderIdEl = document.getElementById('input-order-id');
  const attemptEl = document.getElementById('input-attempt-no');
  const orderId = orderIdEl ? orderIdEl.value.trim() || 'ord_2026_aeth_901' : 'ord_2026_aeth_901';
  const attemptNo = attemptEl ? Number(attemptEl.value || 1) : 1;
  const idemKey = `pi_create_${orderId}_attempt_${attemptNo}`;
  const isBridge = state.selectedPaymentMethod === 'crypto_bridge' || state.selectedPaymentMethod === 'crypto_usdc';

  const { status, data } = await fetchJson('/api/stripe/payment_intents', {
    method: 'POST',
    headers: {
      'Idempotency-Key': idemKey,
    },
    body: JSON.stringify({
      items: state.cart.map((item) => ({ id: item.id, quantity: item.quantity })), // Zero-Trust: only sku_id + quantity
      locale: state.currentLocale,
      vat_id: vatId,
      postal_code: postalCode,
      email: email,
      order_id: orderId,
      attempt_no: attemptNo,
      expand: ['latest_charge.balance_transaction'],
      metadata: {
        order_id: orderId,
        customer_tier: 'enterprise',
        erp_cost_center: 'IT-01',
      },
      capture_method: captureMethod,
      setup_future_usage: setupFutureUsage,
      payment_method_type: state.selectedPaymentMethod,
      bridge_asset: isBridge ? state.bridgeAsset : undefined,
      bridge_chain: isBridge ? state.bridgeChain : undefined,
      bridge_settlement_mode: isBridge ? state.bridgeSettlementMode : undefined,
      test_scenario: isExpress ? 'success_standard' : state.selectedScenario,
      link_instant: isExpress,
    }),
  });

  await refreshTelemetryStreams();

  // Handle HTTP 400 Idempotency Parameter Mismatch or Zero-Trust Violation
  if (status === 400 && data.error) {
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--error">
        <strong>HTTP 400 <code>${data.error.type}</code> (<code>${data.error.code}</code>):</strong><br/>
        ${data.error.message}
      </div>
    `;
    return;
  }

  // Handle HTTP 429 RateLimitError or HTTP 503 APIConnectionError (Transient Errors)
  if ((status === 429 || status === 503) && data.error) {
    const taxo = data.error.exception_taxonomy || {};
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--amber">
        <strong>Transient Infrastructure Error &rarr; <code>${taxo.python_sdk_class || data.error.type}</code> (HTTP ${status}):</strong><br/>
        ${data.error.message}<br/>
        <span style="font-family: var(--font-mono); font-size: 0.72rem;">
          ✓ Auto-Retry Policy: <code>should_auto_retry=${taxo.should_auto_retry}</code> · Backoff: <code>[250ms, 620ms] + jitter</code> · <strong>Reuse SAME Key:</strong> <code>${idemKey}</code>
        </span>
      </div>
    `;
    return;
  }

  const pi = data.payment_intent;
  if (!pi) return;
  state.latestPaymentIntent = pi;
  updateCheckoutStateTrackerNodes(pi.status, Boolean(pi.last_payment_error));
  renderPaymentIntentTelemetryCard(pi);

  if (data.idempotent_replay) {
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--amber">
        <strong>24h Idempotent Cache Replay (<code>Idempotency-Key: ${idemKey}</code>) — Zero Double Charge!</strong><br/>
        Returned cached PaymentIntent <code>${pi.id}</code> (Original Request: <code>${data.idempotency_metadata?.original_request_id}</code> · TTL remaining: <code>${data.idempotency_metadata?.ttl_seconds_remaining}s</code>).
        To create a new PaymentIntent or modify cart items, click <strong>+1 Attempt</strong> or <strong>New Order ID</strong>.
      </div>
    `;
    return;
  }

  if (pi.status === 'requires_action' && pi.next_action) {
    state.pending3DSPaymentIntentId = pi.id;
    document.getElementById('modal-3ds2').classList.add('is-open');
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--amber">
        <strong>State Transition &rarr; <code>requires_action</code> (3DS2 Step-Up Required on <code>${pi.id}</code>):</strong> Complete Strong Customer Authentication in the modal window.
      </div>
    `;
    return;
  }

  if (status === 402 || pi.last_payment_error) {
    // Automatically increment attempt_no so the next retry uses a fresh deterministic key for the new card
    if (attemptEl) {
      attemptEl.value = String(attemptNo + 1);
      updateLiveIdempotencyPreview();
    }
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--error">
        <strong><code>stripe.error.CardError</code> (HTTP 402 Business Decline &rarr; <code>${pi.last_payment_error.decline_code}</code>):</strong> ${pi.last_payment_error.message}
        <br/><span style="font-family: var(--font-mono); font-size: 0.72rem;">Radar Rule: ${pi.radar_evaluation.matched_rule} · Never auto-retry 402 CardError! Attempt # auto-incremented to <code>attempt_${attemptNo + 1}</code> for customer retry.</span>
      </div>
    `;
    return;
  }

  if (pi.status === 'requires_capture') {
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--amber">
        <strong>State Transition &rarr; <code>requires_capture</code> (7-Day Pre-Auth Hold Active):</strong><br/>
        <code>${pi.id}</code> reserved <code>${formatMinorUnitsDirect(pi.amount_capturable)}</code> on the customer's card (<code>amount_received: 0</code>). Use the lifecycle controls on the right to <strong>Capture</strong> or <strong>Void</strong> the hold!
      </div>
    `;
    return;
  }

  if (pi.status === 'processing') {
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--amber">
        <strong>State Transition &rarr; <code>processing</code> (Asynchronous Bank Clearing):</strong><br/>
        <code>${pi.id}</code> submitted to ACH / SEPA clearinghouse rails. Webhook <code>payment_intent.processing</code> emitted; final settlement arrives asynchronously via <code>payment_intent.succeeded</code>.
      </div>
    `;
    return;
  }

  if (pi.bridge_stablecoin_details) {
    const br = pi.bridge_stablecoin_details;
    feedbackEl.innerHTML = `
      <div class="alert-banner alert-banner--success">
        <strong>State Transition &rarr; <code>succeeded</code> via Bridge Stablecoin Orchestration (${br.stablecoin_amount_paid} on ${br.source_chain.toUpperCase()})!</strong><br/>
        Liquidation Address <code>${br.liquidation_address_id}</code> (<code>${br.onchain_deposit_address.slice(0, 12)}...</code>) settled in <code>${br.finality_ms}ms</code> &rarr; <code>${br.destination_currency}</code> · Gas: Sponsored by Bridge Paymaster.
      </div>
    `;
    return;
  }

  const methodTitle = isExpress ? `${expressLabel} (Express 1-Click)` : state.selectedPaymentMethod.toUpperCase();
  feedbackEl.innerHTML = `
    <div class="alert-banner alert-banner--success">
      <strong>State Transition &rarr; <code>succeeded</code> via ${methodTitle}!</strong><br/>
      PaymentIntent <code>${pi.id}</code> captured · Idempotency-Key: <code>${idemKey}</code> · Hydrated <code>latest_charge.balance_transaction</code> in 1 call · Metadata <code>order_id=${orderId}</code> propagated.
    </div>
  `;
}

function updateCheckoutStateTrackerNodes(currentStatus, hasError = false) {
  const allIds = [
    'cnode-requires_payment_method',
    'cnode-requires_confirmation',
    'cnode-requires_action',
    'cnode-processing',
    'cnode-requires_capture',
    'cnode-succeeded',
    'cnode-canceled',
  ];
  allIds.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.className = 'state-pill-node is-visited';
  });

  const targetEl = document.getElementById(`cnode-${currentStatus}`);
  if (targetEl) {
    if (currentStatus === 'succeeded') {
      targetEl.className = 'state-pill-node is-succeeded';
    } else if (hasError || currentStatus === 'canceled') {
      targetEl.className = 'state-pill-node is-error';
    } else {
      targetEl.className = 'state-pill-node is-current';
    }
  }
}

async function confirm3DS2StepUp() {
  const otp = document.getElementById('input-3ds2-otp').value.trim() || '849201';
  const piId = state.pending3DSPaymentIntentId;
  if (!piId) return;

  const { data } = await fetchJson('/api/stripe/payment_intents/confirm_3ds', {
    method: 'POST',
    body: JSON.stringify({
      payment_intent_id: piId,
      otp_code: otp,
    }),
  });

  document.getElementById('modal-3ds2').classList.remove('is-open');
  const pi = data.payment_intent;
  state.latestPaymentIntent = pi;
  updateCheckoutStateTrackerNodes(pi.status, false);
  renderPaymentIntentTelemetryCard(pi);
  await refreshTelemetryStreams();

  document.getElementById('checkout-feedback-banner').innerHTML = `
    <div class="alert-banner alert-banner--success">
      <strong>EMV 3D Secure 2.2 Authenticated &rarr; State: <code>${pi.status}</code>!</strong><br/>
      PaymentIntent <code>${pi.id}</code> · CAVV Cryptogram: <code>${pi.three_d_secure_2_result.cavv}</code> (ECI-05 Liability Shift Active).
    </div>
  `;
}

function renderPaymentIntentTelemetryCard(pi) {
  const box = document.getElementById('latest-pi-telemetry-box');
  box.style.display = 'block';
  document.getElementById('pi-result-status-badge').textContent = pi.status;
  const br = pi.bridge_stablecoin_details;
  const bt = pi.latest_charge && typeof pi.latest_charge === 'object' ? pi.latest_charge.balance_transaction : null;
  const meta = pi.metadata || {};
  const idem = pi.idempotency_protection || {};

  document.getElementById('pi-result-details').innerHTML = `
    <div class="ledger-row"><span>ID:</span><code>${pi.id}</code></div>
    <div class="ledger-row"><span>State Machine Status:</span><strong><code>${pi.status}</code></strong></div>
    <div class="ledger-row"><span>Server Minor Units (Zero-Trust):</span><span>${formatMinorUnitsDirect(pi.amount || 0)} (<code>${pi.amount}</code> minor units)</span></div>
    <div class="ledger-row"><span>Captured / Received:</span><span>${formatMinorUnitsDirect(pi.amount_received || 0)} (${pi.currency.toUpperCase()})</span></div>
    ${idem.idempotency_key ? `<div class="ledger-row"><span>Deterministic Idempotency-Key:</span><code>${idem.idempotency_key}</code></div>` : ''}
    ${meta.order_id ? `<div class="ledger-row"><span>Propagated Metadata:</span><code>order_id=${meta.order_id} · tier=${meta.customer_tier} · cc=${meta.erp_cost_center}</code></div>` : ''}
    ${
      bt
        ? `<div class="ledger-row" style="color: var(--accent-link-green);"><span>Expanded BalanceTxn (1-Call):</span><code>Net: ${formatMinorUnitsDirect(bt.net)} · Fee: ${formatMinorUnitsDirect(bt.fee)} · FX: ${bt.exchange_rate}</code></div>`
        : ''
    }
    <div class="ledger-row"><span>Radar Risk Score:</span><span>${pi.radar_evaluation?.risk_score ?? 10}/100 (${pi.radar_evaluation?.risk_level || 'normal'})</span></div>
    ${
      br
        ? `<div class="ledger-row" style="color: var(--accent-cobalt);"><span>Bridge Stablecoin Rail:</span><code>${br.stablecoin_amount_paid} (${br.source_chain})</code></div>
           <div class="ledger-row"><span>Bridge Liquidation ID:</span><code>${br.liquidation_address_id}</code></div>`
        : ''
    }
    ${pi.transfer_group ? `<div class="ledger-row"><span>Connect Transfer Group:</span><code>${pi.transfer_group}</code></div>` : ''}
    ${pi.refunded ? `<div class="ledger-row" style="color: var(--accent-amber);"><span>Refunded Amount:</span><strong>${formatMinorUnitsDirect(pi.amount_refunded)}</strong></div>` : ''}
  `;

  const actionsEl = document.getElementById('pi-post-auth-actions');
  if (pi.status === 'requires_capture') {
    actionsEl.innerHTML = `
      <button type="button" class="btn btn--link-green" onclick="captureCheckoutHold('${pi.id}', 'full')">
        ✓ Capture Full Hold (${formatMinorUnitsDirect(pi.amount)})
      </button>
      <button type="button" class="btn" onclick="captureCheckoutHold('${pi.id}', 'partial_75_pct')">
        Capture Partial (75%)
      </button>
      <button type="button" class="btn" onclick="cancelCheckoutHold('${pi.id}')">
        ✕ Void Hold (/cancel · $0 Fee)
      </button>
    `;
  } else if (pi.status === 'processing') {
    actionsEl.innerHTML = `
      <button type="button" class="btn btn--link-green" onclick="captureCheckoutHold('${pi.id}', 'full')">
        ✓ Simulate ACH/SEPA Clearing Settlement (&rarr; succeeded)
      </button>
      <button type="button" class="btn" onclick="cancelCheckoutHold('${pi.id}')">
        ✕ Cancel Pending Debit
      </button>
    `;
  } else if (pi.status === 'succeeded' && !pi.refunded) {
    actionsEl.innerHTML = `
      <button type="button" class="btn" onclick="refundCheckoutCharge('${pi.id}', 'full')">
        ↩ Refund + Reverse Connect Split (/v1/refunds)
      </button>
      <button type="button" class="btn" onclick="executeStateMachineTransition('dispute_defense', 11)">
        🛡️ Simulate Dispute + 3DS2 Liability Shift Win
      </button>
    `;
  } else {
    actionsEl.innerHTML = '';
  }
}

window.captureCheckoutHold = async function (piId, captureStrategy = 'full') {
  const { data } = await fetchJson('/api/stripe/payment_intents/capture', {
    method: 'POST',
    body: JSON.stringify({ payment_intent_id: piId, capture_strategy: captureStrategy }),
  });
  const pi = data.payment_intent;
  state.latestPaymentIntent = pi;
  updateCheckoutStateTrackerNodes(pi.status, false);
  renderPaymentIntentTelemetryCard(pi);
  await refreshTelemetryStreams();
  document.getElementById('checkout-feedback-banner').innerHTML = `
    <div class="alert-banner alert-banner--success">
      <strong>Manual Capture Succeeded (<code>/v1/payment_intents/${pi.id}/capture</code> · strategy: <code>${captureStrategy}</code>)!</strong><br/>
      Captured <code>${formatMinorUnitsDirect(pi.amount_received)}</code> · BalanceTransaction <code>${pi.balance_transaction.id}</code> settled.
    </div>
  `;
};

window.cancelCheckoutHold = async function (piId) {
  const { data } = await fetchJson('/api/stripe/payment_intents/cancel', {
    method: 'POST',
    body: JSON.stringify({ payment_intent_id: piId, cancellation_reason: 'requested_by_customer' }),
  });
  const pi = data.payment_intent;
  state.latestPaymentIntent = pi;
  updateCheckoutStateTrackerNodes('canceled', true);
  renderPaymentIntentTelemetryCard(pi);
  await refreshTelemetryStreams();
  document.getElementById('checkout-feedback-banner').innerHTML = `
    <div class="alert-banner alert-banner--amber">
      <strong>Authorization Hold Voided (<code>status: canceled</code>)!</strong><br/>
      Reserved funds released back to customer's card with zero interchange processing fees.
    </div>
  `;
};

window.refundCheckoutCharge = async function (piId, refundStrategy = 'full') {
  const { data } = await fetchJson('/api/stripe/refunds', {
    method: 'POST',
    body: JSON.stringify({
      payment_intent_id: piId,
      refund_strategy: refundStrategy,
      reverse_transfer: true,
      refund_application_fee: true,
    }),
  });
  if (data.payment_intent) {
    state.latestPaymentIntent = data.payment_intent;
    renderPaymentIntentTelemetryCard(data.payment_intent);
  }
  updateCheckoutStateTrackerNodes('canceled', false);
  await refreshTelemetryStreams();
  document.getElementById('checkout-feedback-banner').innerHTML = `
    <div class="alert-banner alert-banner--amber">
      <strong>Refund Succeeded (<code>${data.refund.id}</code>) with Proportional Connect Transfer Reversal!</strong><br/>
      <code>reverse_transfer=true</code> clawed back partner funds via <code>${data.refund.transfer_reversal}</code> and refunded platform fee.
    </div>
  `;
};

// ==========================================================================
// 4. STRIPE BILLING + METRONOME USAGE METERS
// ==========================================================================

function renderBillingMeterView() {
  const m = state.meterUsage;
  if (!m) return;

  const used = m.current_period_seconds;
  const inc = m.included_seconds;
  const overageSec = Math.max(0, used - inc);
  const overageCents = Math.round((overageSec / 100) * m.rate_usd_cents_per_100s);
  const totalCents = 3900 + overageCents;

  document.getElementById('meter-used-sec').textContent = used.toLocaleString('en-US');
  const pct = Math.min(100, Math.round((used / (inc * 1.6)) * 100));
  const fillEl = document.getElementById('meter-bar-fill');
  fillEl.style.width = `${pct}%`;
  fillEl.classList.toggle('is-overage', overageSec > 0);

  document.getElementById('meter-overage-status').textContent =
    overageSec > 0
      ? `Metered Overage Active: +${overageSec.toLocaleString('en-US')} DSP seconds billed at $0.004/sec`
      : `${(inc - used).toLocaleString('en-US')} included DSP seconds remaining before overage`;

  document.getElementById('invoice-overage-sec').textContent = overageSec.toLocaleString('en-US');
  document.getElementById('invoice-overage-amount').textContent = `$${(overageCents / 100).toFixed(2)}`;
  document.getElementById('invoice-total-preview').textContent = `$${(totalCents / 100).toFixed(2)}`;

  const tbody = document.getElementById('meter-events-tbody');
  tbody.innerHTML = (m.events || [])
    .map(
      (ev) => `
        <tr>
          <td><code>${ev.id}</code></td>
          <td>${ev.workload}</td>
          <td><strong>+${ev.value.toLocaleString('en-US')}s</strong></td>
          <td><code>${ev.idempotency_key}</code></td>
        </tr>
      `
    )
    .join('');
}

async function ingestMeterEvent(seconds, workloadLabel) {
  const { data } = await fetchJson('/api/stripe/billing/meter_events', {
    method: 'POST',
    body: JSON.stringify({
      value: seconds,
      workload: workloadLabel,
    }),
  });
  state.meterUsage = data.meter;
  renderBillingMeterView();
  await refreshTelemetryStreams();
}

// ==========================================================================
// 5. STRIPE AGENTIC COMMERCE & CONNECT ACCOUNTS V2
// ==========================================================================

async function runAgenticOrderIntent() {
  const mandate = document.getElementById('select-agent-mandate').value;
  const { data } = await fetchJson('/api/stripe/agentic/order_intents', {
    method: 'POST',
    body: JSON.stringify({
      mandate: mandate,
      budget_limit_usd_cents: 140000,
      locale: state.currentLocale,
    }),
  });

  const resEl = document.getElementById('agentic-intent-result');
  resEl.style.display = 'flex';
  const dpt = data.delegated_payment_token;

  resEl.innerHTML = `
    <div class="ledger-row">
      <strong>Agentic OrderIntent ID</strong>
      <code class="ledger-mono">${data.id}</code>
    </div>
    <div class="ledger-row">
      <span>Scoped Delegated Payment Token</span>
      <code class="ledger-mono" style="color: var(--accent-cobalt);">${dpt.id}</code>
    </div>
    <div class="ledger-row">
      <span>Cryptographic Spend Ceiling</span>
      <span class="ledger-mono">${ data.calculation.formatted.total } (${dpt.currency.toUpperCase()} · Single-Use)</span>
    </div>
    <div class="ledger-row">
      <span>Allowed Merchant Category (MCC Lock)</span>
      <code class="ledger-mono">5733 (Music Stores) / 5734 (Software)</code>
    </div>
    <p style="font-size: 0.78rem; color: var(--ink-secondary); margin: 0.45rem 0;">
      <strong>AI Agent Rationale:</strong> ${data.rationale}
    </p>
    <button type="button" class="btn btn--link-green" onclick="applyAgenticBundleToCart(${JSON.stringify(data.recommended_items).replace(/"/g, '&quot;')})">
      ✓ Approve Agentic Bundle &amp; Load into Optimized Checkout
    </button>
  `;

  await refreshTelemetryStreams();
}

window.applyAgenticBundleToCart = async function (recommendedItems) {
  state.cart = recommendedItems;
  updateCartBadges();
  await recalculateCartAndTax();
  switchView('checkout');
};

async function createConnectV2Account() {
  const studioName = document.getElementById('input-connect-studio-name').value.trim() || 'Nordic Modular Lab AB';
  const country = document.getElementById('select-connect-country').value;

  const { data } = await fetchJson('/api/stripe/connect/accounts', {
    method: 'POST',
    body: JSON.stringify({
      studio_name: studioName,
      country: country,
    }),
  });

  const listEl = document.getElementById('connect-accounts-list');
  const div = document.createElement('div');
  div.className = 'split-item';
  div.innerHTML = `
    <div class="ledger-row">
      <strong>${data.display_name} (${data.identity.country})</strong>
      <code>${data.id}</code>
    </div>
    <div style="color: var(--accent-link-green); margin-top: 0.2rem;">
      ✓ Provisioned via <code>/v2/core/accounts</code> · <code>losses.payments=stripe</code> · 12% Platform Fee
    </div>
  `;
  listEl.prepend(div);
  await refreshTelemetryStreams();
}

async function issueVirtualCommercialCard() {
  const holder = document.getElementById('input-issuing-holder').value.trim() || 'Aetheria Touring Acoustic Engineer';
  const limitUsd = parseFloat(document.getElementById('input-issuing-limit').value) || 2500;
  const limitCents = Math.round(limitUsd * 100);

  const { data } = await fetchJson('/api/stripe/issuing/cards', {
    method: 'POST',
    body: JSON.stringify({
      cardholder_name: holder,
      spend_limit_cents: limitCents,
    }),
  });

  const resEl = document.getElementById('issuing-card-result');
  resEl.style.display = 'flex';
  const auth = data.simulated_realtime_authorization;
  resEl.innerHTML = `
    <div class="ledger-row">
      <strong>Issued Virtual Card ID</strong>
      <code class="ledger-mono">${data.id} (•••• ${data.last4})</code>
    </div>
    <div class="ledger-row">
      <span>Treasury Financial Account</span>
      <code class="ledger-mono">${data.treasury_financial_account}</code>
    </div>
    <div class="ledger-row">
      <span>Spend Control Limit</span>
      <span class="ledger-mono">$${(limitCents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })} / authorization</span>
    </div>
    <div class="ledger-row" style="color: var(--accent-link-green);">
      <span>Real-Time Auth Webhook (<code>issuing_authorization.request</code>)</span>
      <strong class="ledger-mono">APPROVED in ${auth.webhook_response_sla_ms}ms (${auth.id})</strong>
    </div>
  `;
  await refreshTelemetryStreams();
}

async function runSetupIntentVaulting() {
  const { data } = await fetchJson('/api/stripe/setup_intents', {
    method: 'POST',
    body: JSON.stringify({
      usage: 'off_session',
      payment_method_type: 'card',
    }),
  });

  const resEl = document.getElementById('setup-intent-result');
  resEl.style.display = 'flex';
  resEl.innerHTML = `
    <div class="ledger-row">
      <strong>SetupIntent ID</strong>
      <code class="ledger-mono">${data.id} (status: ${data.status})</code>
    </div>
    <div class="ledger-row">
      <span>Vaulted PaymentMethod</span>
      <code class="ledger-mono">${data.payment_method}</code>
    </div>
    <div class="ledger-row">
      <span>Network Token (Visa VTS / MDES)</span>
      <code class="ledger-mono" style="color: var(--accent-cobalt);">${data.network_tokenization.network_token_id}</code>
    </div>
    <div class="ledger-row">
      <span>MIT Mandate Exemption</span>
      <code class="ledger-mono">${data.mandate} (${data.network_tokenization.mit_exemption})</code>
    </div>
  `;
  await refreshTelemetryStreams();
}

async function createBridgeLiquidationAddress() {
  const chain = document.getElementById('select-bridge-liq-chain').value;
  const asset = document.getElementById('select-bridge-liq-asset').value;
  const dest = document.getElementById('select-bridge-liq-dest').value;

  const { data } = await fetchJson('/api/stripe/bridge/orchestrate', {
    method: 'POST',
    body: JSON.stringify({
      operation: 'create_liquidation_address',
      chain: chain,
      asset: asset,
      destination_type: dest,
    }),
  });

  const resEl = document.getElementById('bridge-liquidation-result');
  resEl.style.display = 'flex';
  resEl.innerHTML = `
    <div class="ledger-row">
      <strong>Bridge Liquidation Address ID</strong>
      <code class="ledger-mono">${data.id}</code>
    </div>
    <div class="ledger-row">
      <span>On-Chain Deposit Address (${data.chain.toUpperCase()} · ${data.currency.toUpperCase()})</span>
      <code class="ledger-mono" style="color: var(--accent-cobalt);">${data.address.slice(0, 18)}...${data.address.slice(-6)}</code>
    </div>
    <div class="ledger-row">
      <span>Auto-Settlement Destination</span>
      <code class="ledger-mono">${data.destination_payment_rail} &rarr; ${data.destination_currency.toUpperCase()}</code>
    </div>
    <div class="ledger-row" style="color: var(--accent-link-green);">
      <span>Paymaster Gas Sponsorship</span>
      <strong class="ledger-mono">ACTIVE (ERC-4337 / Solana Fee Payer · $0 Gas)</strong>
    </div>
  `;
  await refreshTelemetryStreams();
}

async function runBridgeCrossBorderPayout() {
  const recipient = document.getElementById('select-bridge-payout-recipient').value;
  const amountUsd = parseFloat(document.getElementById('input-bridge-payout-amount').value) || 1250;
  const chain = document.getElementById('select-bridge-payout-chain').value;
  const asset = document.getElementById('select-bridge-payout-asset').value;

  const { data } = await fetchJson('/api/stripe/bridge/orchestrate', {
    method: 'POST',
    body: JSON.stringify({
      operation: 'cross_border_payout',
      recipient_name: recipient,
      amount_usd: amountUsd,
      chain: chain,
      asset: asset,
    }),
  });

  const resEl = document.getElementById('bridge-payout-result');
  resEl.style.display = 'flex';
  resEl.innerHTML = `
    <div class="ledger-row">
      <strong>Bridge Transfer ID</strong>
      <code class="ledger-mono">${data.id} (${data.state})</code>
    </div>
    <div class="ledger-row">
      <span>Source &rarr; Destination Rail</span>
      <code class="ledger-mono">Stripe USD Balance &rarr; ${data.destination.currency.toUpperCase()} on ${data.destination.payment_rail.toUpperCase()}</code>
    </div>
    <div class="ledger-row">
      <span>Recipient Studio</span>
      <span>${data.destination.recipient_studio}</span>
    </div>
    <div class="ledger-row" style="color: var(--accent-link-green);">
      <span>Final Settled Amount (${data.receipt.settlement_latency_ms}ms)</span>
      <strong class="ledger-mono">${data.receipt.final_amount} (Tx: ${data.receipt.tx_hash.slice(0, 14)}...)</strong>
    </div>
  `;
  await refreshTelemetryStreams();
}

// ==========================================================================
// 6. RUNTIME API CONFIGURATION & DEVELOPER INSPECTOR DRAWER
// ==========================================================================

async function saveRuntimeApiConfig() {
  const mode = document.getElementById('select-api-mode').value;
  const pk = document.getElementById('input-pk-key').value.trim();
  const sk = document.getElementById('input-sk-key').value.trim();

  const { data } = await fetchJson('/api/config', {
    method: 'POST',
    body: JSON.stringify({
      mode: mode,
      publishable_key: pk,
      secret_key: sk,
    }),
  });

  document.getElementById('telemetry-mode-text').textContent =
    data.mode === 'live_stripe_api'
      ? 'LIVE STRIPE TEST API PASSTHROUGH ACTIVE'
      : 'SANDBOX SIMULATOR + LIVE API READY';
  document.getElementById('modal-api-config').classList.remove('is-open');
}

function renderDeveloperInspector() {
  const listEl = document.getElementById('dev-stream-list');
  const combined = [
    ...state.apiLogs.map((a) => ({
      itemType: 'API',
      id: a.id,
      title: `${a.method} ${a.endpoint}`,
      subtitle: `${a.status_code} OK · ${a.latency_ms}ms`,
      timestamp: a.timestamp_iso,
      raw: a,
    })),
    ...state.webhookEvents.map((w) => ({
      itemType: 'WEBHOOK',
      id: w.id,
      title: w.type,
      subtitle: `Signed evt · ${w.created_iso}`,
      timestamp: w.created_iso,
      raw: w,
    })),
  ];

  if (combined.length > 0) {
    document.getElementById('dev-bar-latest-event').textContent =
      `Latest: ${combined[0].title} (${combined[0].subtitle})`;
  }

  listEl.innerHTML = combined
    .map((item, idx) => {
      const isSelected = state.selectedInspectorItemId
        ? state.selectedInspectorItemId === item.id
        : idx === 0;
      if (isSelected && !state.selectedInspectorItemId) {
        state.selectedInspectorItemId = item.id;
        displayInspectorPayload(item);
      }
      const badgeColor = item.itemType === 'API' ? 'hsl(210, 85%, 65%)' : 'hsl(158, 75%, 62%)';
      return `
        <div class="dev-stream-item ${isSelected ? 'is-selected' : ''}" onclick="selectInspectorItem('${item.id}')">
          <div>
            <span style="color: ${badgeColor}; font-weight: 700;">[${item.itemType}]</span>
            <strong>${item.title}</strong>
          </div>
          <span style="color: var(--ink-muted-dark);">${item.subtitle}</span>
        </div>
      `;
    })
    .join('');
}

window.selectInspectorItem = function (itemId) {
  state.selectedInspectorItemId = itemId;
  const apiMatch = state.apiLogs.find((a) => a.id === itemId);
  if (apiMatch) {
    displayInspectorPayload({ itemType: 'API', raw: apiMatch });
  } else {
    const whMatch = state.webhookEvents.find((w) => w.id === itemId);
    if (whMatch) {
      displayInspectorPayload({ itemType: 'WEBHOOK', raw: whMatch });
    }
  }
  renderDeveloperInspector();
};

function displayInspectorPayload(item) {
  const viewer = document.getElementById('dev-payload-viewer');
  if (item.itemType === 'API') {
    const a = item.raw;
    viewer.textContent =
      `// STRIPE REST API CALL (${a.api_version}) — ${a.method} ${a.endpoint}\n` +
      `// Mode: ${a.mode} | Status: ${a.status_code} | Latency: ${a.latency_ms}ms\n\n` +
      `/* Equivalent cURL Command */\n${a.curl_snippet}\n\n` +
      `/* Request Body */\n${JSON.stringify(a.request_body, null, 2)}\n\n` +
      `/* Stripe API Response */\n${JSON.stringify(a.response_body, null, 2)}`;
  } else {
    const w = item.raw;
    viewer.textContent =
      `// STRIPE SIGNED WEBHOOK EVENT — ${w.type}\n` +
      `// Event ID: ${w.id} | Timestamp: ${w.created_iso}\n` +
      `// HTTP Header -> Stripe-Signature: ${w.stripe_signature}\n\n` +
      `${JSON.stringify(w.payload, null, 2)}`;
  }
}

// ==========================================================================
// 7. STEP-BY-STEP PAYMENT STATE MACHINE & STRIPE API ACADEMY (12 STEPS)
// ==========================================================================

const STATE_MACHINE_CURRICULUM = [
  {
    stepNum: 1,
    stateBadge: 'pre_intent_quote',
    title: 'Pre-Intent Adaptive Pricing, FX Quote & Tax Calculation',
    endpoint: 'POST /v1/tax/calculations + POST /v1/fx_quotes',
    sandboxAction: null,
    summary:
      'Before creating a PaymentIntent, your server computes exact local currency prices via Stripe Adaptive Pricing (locking FX conversion rates for 30 minutes) and calculates rooftop-accurate VAT/Sales Tax via the Stripe Tax API.',
    clientRole:
      'Collects shipping country, postal code, and optional EU B2B VAT ID via Stripe Address Element (`stripe.elements().create("address")`).',
    serverRole:
      'Calls `POST /v1/tax/calculations` with `line_items`, product tax codes (`txcd_99999999` physical vs `txcd_10103001` SaaS), and `customer_details`.',
    stripeRole:
      'Validates EU VAT IDs against VIES in real time (applying 0% Reverse Charge when valid) and returns an immutable `taxcalc_...` ID to link into the PaymentIntent.',
    webhookRule:
      'Emits `tax.calculation.created`. Note: A Tax Calculation is a read-only quote and does NOT appear on government tax returns until the linked PaymentIntent reaches `succeeded`.',
    code: {
      curl: `curl https://api.stripe.com/v1/tax/calculations \\
  -u sk_test_51Q9...: \\
  -H "Stripe-Version: 2026-02-25.clover" \\
  -d currency=eur \\
  -d "customer_details[address][country]=DE" \\
  -d "customer_details[address][postal_code]=10115" \\
  -d "customer_details[tax_ids][0][type]=eu_vat" \\
  -d "customer_details[tax_ids][0][value]=DE811907980" \\
  -d "line_items[0][amount]=78108" \\
  -d "line_items[0][tax_code]=txcd_99999999"`,
      node: `const taxCalculation = await stripe.tax.calculations.create({
  currency: 'eur',
  customer_details: {
    address: { country: 'DE', postal_code: '10115' },
    address_source: 'shipping',
    tax_ids: [{ type: 'eu_vat', value: 'DE811907980' }],
  },
  line_items: [
    { amount: 78108, reference: 'prod_synth_mk2', tax_code: 'txcd_99999999' },
  ],
});`,
      python: `tax_calculation = stripe.tax.Calculation.create(
    currency="eur",
    customer_details={
        "address": {"country": "DE", "postal_code": "10115"},
        "address_source": "shipping",
        "tax_ids": [{"type": "eu_vat", "value": "DE811907980"}],
    },
    line_items=[
        {"amount": 78108, "reference": "prod_synth_mk2", "tax_code": "txcd_99999999"},
    ],
)`,
      go: `params := &stripe.TaxCalculationParams{
  Currency: stripe.String(string(stripe.CurrencyEUR)),
  CustomerDetails: &stripe.TaxCalculationCustomerDetailsParams{
    Address: &stripe.AddressParams{Country: stripe.String("DE"), PostalCode: stripe.String("10115")},
    AddressSource: stripe.String("shipping"),
  },
}
calc, err := calculation.New(params)`,
    },
  },
  {
    stepNum: 2,
    stateBadge: 'requires_payment_method',
    title: 'Intent Initialization (Root State: requires_payment_method)',
    endpoint: 'POST /v1/payment_intents',
    sandboxAction: { label: '▶ Run Step 2 in Sandbox: Create PaymentIntent', action: 'create' },
    summary:
      'Every Stripe checkout begins by creating a `PaymentIntent` on your backend server. It starts in `status: requires_payment_method` because no customer payment credential has been attached yet. Never create PaymentIntents from the browser.',
    clientRole:
      'Receives only the scoped `client_secret` (`pi_..._secret_...`) from your backend and mounts the Stripe Payment Element (`elements.create("payment")`).',
    serverRole:
      'Calls `POST /v1/payment_intents` with an `Idempotency-Key` header, exact `amount` in minor units, `currency`, `automatic_payment_methods[enabled]=true`, and `hooks[inputs][tax][calculation]`.',
    stripeRole:
      'Initializes the state machine ledger, evaluates AI-ordered regional payment methods for the buyer locale, and generates the `client_secret`.',
    webhookRule:
      'Emits `payment_intent.created`. Always pass a deterministic `Idempotency-Key` (e.g., `cart_session_id +IncrVersion`) so network retries never create duplicate intents.',
    code: {
      curl: `curl https://api.stripe.com/v1/payment_intents \\
  -u sk_test_51Q9...: \\
  -H "Idempotency-Key: idem_order_994810" \\
  -d amount=84900 \\
  -d currency=usd \\
  -d "automatic_payment_methods[enabled]=true" \\
  -d "hooks[inputs][tax][calculation]=taxcalc_1Q9..." \\
  -d setup_future_usage=off_session`,
      node: `const paymentIntent = await stripe.paymentIntents.create({
  amount: 84900,
  currency: 'usd',
  automatic_payment_methods: { enabled: true },
  setup_future_usage: 'off_session',
  hooks: { inputs: { tax: { calculation: taxCalculation.id } } },
}, { idempotencyKey: 'idem_order_994810' });`,
      python: `payment_intent = stripe.PaymentIntent.create(
    amount=84900,
    currency="usd",
    automatic_payment_methods={"enabled": True},
    setup_future_usage="off_session",
    hooks={"inputs": {"tax": {"calculation": tax_calculation.id}}},
    idempotency_key="idem_order_994810",
)`,
      go: `params := &stripe.PaymentIntentParams{
  Amount: stripe.Int64(84900),
  Currency: stripe.String(string(stripe.CurrencyUSD)),
  AutomaticPaymentMethods: &stripe.PaymentIntentAutomaticPaymentMethodsParams{Enabled: stripe.Bool(true)},
  SetupFutureUsage: stripe.String("off_session"),
}
params.SetIdempotencyKey("idem_order_994810")
pi, err := paymentintent.New(params)`,
    },
  },
  {
    stepNum: 3,
    stateBadge: 'pm_tokenized',
    title: 'Client-Side Vaulting & Network Tokenization (PCI SAQ-A)',
    endpoint: 'stripe.elements().submit() -> POST /v1/payment_methods',
    sandboxAction: { label: '▶ Run Step 3 in Sandbox: Mint & Attach Network Token PM', action: 'attach_pm' },
    summary:
      'When the buyer enters a card, Link passkey, or Apple Pay credential, `Stripe.js` tokenizes the sensitive data directly from its cross-origin iframe to Stripe Vault (`pm_...`) and provisions a Visa VTS / Mastercard MDES Network Token (`ntok_...`).',
    clientRole:
      'Executes `await elements.submit()` to validate form fields and tokenize the credential inside Stripe cross-origin iframes without exposing PAN/CVC to your DOM.',
    serverRole:
      'Zero involvement in raw PAN handling — keeps your infrastructure in the lowest PCI DSS SAQ-A compliance tier.',
    stripeRole:
      'Exchanges the primary account number (PAN) with Visa/Mastercard token vaults for a merchant-specific Network Token (`ntok_vts_...`) and dynamic ECI-05 cryptogram.',
    webhookRule:
      'When `setup_future_usage=off_session` or `SetupIntent` is used, emits `payment_method.attached` and enables Card Account Updater for automatic expiry rotation.',
    code: {
      curl: `# Executed automatically by Stripe.js inside the isolated PCI iframe:
curl https://api.stripe.com/v1/payment_methods \\
  -u pk_test_51Q9...: \\
  -d type=card \\
  -d "card[token]=tok_visa_network_tokenized"`,
      node: `// Client-side Stripe.js v3
const { error: submitError } = await elements.submit();
if (submitError) {
  showError(submitError.message);
  return;
}`,
      python: `# Server-side inspection of Network Token metadata on a PaymentMethod:
pm = stripe.PaymentMethod.retrieve("pm_1Q9NetToken...")
print(pm.card.networks.preferred, pm.card.checks.cvc_check)`,
      go: `pm, err := paymentmethod.Get("pm_1Q9NetToken...", nil)
fmt.Println("Network Token Brand:", pm.Card.Brand)`,
    },
  },
  {
    stepNum: 4,
    stateBadge: 'requires_confirmation',
    title: 'PaymentMethod Attached (status: requires_confirmation)',
    endpoint: 'POST /v1/payment_intents/:id',
    sandboxAction: { label: '▶ Run Step 4 in Sandbox: Transition to requires_confirmation', action: 'attach_pm' },
    summary:
      'Once a `PaymentMethod` (`pm_...`) is attached to the `PaymentIntent` (either explicitly via API or during two-step confirmation), the state machine transitions to `requires_confirmation`, indicating the intent is ready to execute.',
    clientRole:
      'Can display a final order review screen (e.g., showing exact shipping & card last4) before the buyer clicks "Confirm & Pay".',
    serverRole:
      'Optionally updates final shipping costs or metadata on `POST /v1/payment_intents/:id` before calling `/confirm`.',
    stripeRole:
      'Validates that the attached `PaymentMethod` currency and rail capabilities match the `PaymentIntent` configuration.',
    webhookRule:
      'No money has moved yet. In single-step `stripe.confirmPayment()`, Stripe transitions through `requires_confirmation` atomically in a single API call.',
    code: {
      curl: `curl https://api.stripe.com/v1/payment_intents/pi_3Q9StateLab... \\
  -u sk_test_51Q9...: \\
  -d payment_method=pm_1Q9NetToken...`,
      node: `const updatedIntent = await stripe.paymentIntents.update(
  'pi_3Q9StateLab...',
  { payment_method: 'pm_1Q9NetToken...' }
);
// updatedIntent.status === 'requires_confirmation'`,
      python: `updated_intent = stripe.PaymentIntent.modify(
    "pi_3Q9StateLab...",
    payment_method="pm_1Q9NetToken...",
)
assert updated_intent.status == "requires_confirmation"`,
      go: `params := &stripe.PaymentIntentParams{
  PaymentMethod: stripe.String("pm_1Q9NetToken..."),
}
pi, err := paymentintent.Update("pi_3Q9StateLab...", params)`,
    },
  },
  {
    stepNum: 5,
    stateBadge: 'radar_evaluation',
    title: 'Confirmation & Stripe Radar AI Fraud Scoring (POST /confirm)',
    endpoint: 'POST /v1/payment_intents/:id/confirm',
    sandboxAction: { label: '▶ Run Step 5 in Sandbox: Confirm & Trigger Radar Evaluation', action: 'require_3ds2' },
    summary:
      'Calling `/confirm` (or `stripe.confirmPayment()` from the browser) triggers Stripe Radar AI. Radar scores the transaction from `0` to `99` in `<100ms` using global network telemetry, device fingerprinting, proxy detection, and custom merchant rules.',
    clientRole:
      'Calls `stripe.confirmPayment({ elements, confirmParams: { return_url } })`, transmitting telemetry signals from Stripe.js.',
    serverRole:
      'Can pass `radar_options[session]` or custom metadata attributes evaluated by Radar rules (e.g., `block_if_risk_score_gt_85`).',
    stripeRole:
      'Executes Radar ML models: (1) If `risk_score > 85`, blocks immediately (`card_declined: fraudulent`); (2) If `risk_score > 35` or PSD2 applies, transitions to `requires_action`; (3) Otherwise routes to issuer.',
    webhookRule:
      'If Radar blocks the charge, emits `payment_intent.payment_failed` and `radar.early_fraud_warning.created` (if issuer flags post-auth fraud).',
    code: {
      curl: `curl https://api.stripe.com/v1/payment_intents/pi_3Q9StateLab.../confirm \\
  -u sk_test_51Q9...: \\
  -d return_url="https://store.aetheria.io/checkout/complete"`,
      node: `// Browser Stripe.js confirmation:
const { error } = await stripe.confirmPayment({
  elements,
  confirmParams: {
    return_url: 'https://store.aetheria.io/checkout/complete',
  },
});`,
      python: `confirmed = stripe.PaymentIntent.confirm(
    "pi_3Q9StateLab...",
    return_url="https://store.aetheria.io/checkout/complete",
)`,
      go: `params := &stripe.PaymentIntentConfirmParams{
  ReturnURL: stripe.String("https://store.aetheria.io/checkout/complete"),
}
pi, err := paymentintent.Confirm("pi_3Q9StateLab...", params)`,
    },
  },
  {
    stepNum: 6,
    stateBadge: 'requires_action',
    title: 'EMV 3D Secure 2.2 Step-Up Challenge (status: requires_action)',
    endpoint: 'next_action.use_stripe_sdk (EMV 3DS2 v2.2)',
    sandboxAction: { label: '▶ Run Step 6 in Sandbox: Pause at requires_action (3DS2)', action: 'require_3ds2' },
    summary:
      'When PSD2 Strong Customer Authentication (SCA) or Stripe Radar requires step-up authentication, the PaymentIntent enters `status: requires_action` and populates `next_action.use_stripe_sdk` with the EMV 3DS2 directory server challenge URL.',
    clientRole:
      '`stripe.confirmPayment()` automatically inspects `next_action` and opens the native banking biometric / OTP challenge modal or redirect.',
    serverRole:
      'Must NOT fulfill the order while in `requires_action`. Waits for the asynchronous `payment_intent.succeeded` webhook after the buyer completes 3DS2.',
    stripeRole:
      'Coordinates the EMVCo 3DS2 v2.2 cryptographic exchange with the issuing bank (`visa_emv_3ds2_v2.2`), obtaining the `CAVV` cryptogram and `ECI-05` liability shift.',
    webhookRule:
      'Emits `payment_intent.requires_action`. If the customer abandons the 3DS2 modal, the intent stays in `requires_action` until expired or canceled.',
    code: {
      curl: `# Inspecting a PaymentIntent paused in requires_action:
curl https://api.stripe.com/v1/payment_intents/pi_3Q9StateLab... \\
  -u sk_test_51Q9...:
# Response includes:
# "status": "requires_action",
# "next_action": { "type": "use_stripe_sdk", "directory_server": "visa_emv_3ds2_v2.2" }`,
      node: `// Stripe.js handles 3DS2 challenges automatically inside confirmPayment():
const { paymentIntent, error } = await stripe.confirmPayment({
  elements,
  redirect: 'if_required',
});
if (paymentIntent.status === 'succeeded') {
  console.log('3DS2 CAVV Verified with Liability Shift!');
}`,
      python: `pi = stripe.PaymentIntent.retrieve("pi_3Q9StateLab...")
if pi.status == "requires_action":
    print("Awaiting customer 3DS2 challenge:", pi.next_action.type)`,
      go: `pi, _ := paymentintent.Get("pi_3Q9StateLab...", nil)
if pi.Status == stripe.PaymentIntentStatusRequiresAction {
  fmt.Println("Next action:", pi.NextAction.Type)
}`,
    },
  },
  {
    stepNum: 7,
    stateBadge: 'processing',
    title: 'Asynchronous Bank Debit Clearing (status: processing)',
    endpoint: 'POST /v1/payment_intents/:id/confirm (ACH / SEPA / Konbini)',
    sandboxAction: { label: '▶ Run Step 7 in Sandbox: Enter processing (ACH/SEPA)', action: 'async_processing' },
    summary:
      'For bank debits (`us_bank_account` via Financial Connections, `sepa_debit` in EUR, or `konbini` cash vouchers in JP), settlement is not instant. After customer confirmation, the PaymentIntent enters `status: processing` while funds clear across interbank rails (T+1 to T+4 days).',
    clientRole:
      'Displays a "Payment Processing — We will email your receipt once your bank clears the transfer" confirmation screen.',
    serverRole:
      'Listens for `payment_intent.processing` to lock inventory reservation, and waits for `payment_intent.succeeded` before shipping high-value hardware.',
    stripeRole:
      'Submits the Nacha ACH or SEPA Core Direct Debit mandate batch and monitors clearinghouse settlement or return codes (`R01 Insufficient Funds`).',
    webhookRule:
      'Emits `payment_intent.processing` immediately, followed days later by `payment_intent.succeeded` (or `payment_intent.payment_failed` if the bank debit bounces).',
    code: {
      curl: `curl https://api.stripe.com/v1/payment_intents \\
  -u sk_test_51Q9...: \\
  -d amount=84900 -d currency=eur \\
  -d "payment_method_types[]=sepa_debit" \\
  -d payment_method=pm_sepa_debit_de89370400440532013000 \\
  -d confirm=true`,
      node: `const pi = await stripe.paymentIntents.create({
  amount: 84900,
  currency: 'eur',
  payment_method_types: ['sepa_debit'],
  payment_method: 'pm_sepa_debit_...',
  confirm: true,
});
// pi.status === 'processing'`,
      python: `pi = stripe.PaymentIntent.create(
    amount=84900,
    currency="eur",
    payment_method_types=["sepa_debit"],
    payment_method="pm_sepa_debit_...",
    confirm=True,
)
assert pi.status == "processing"`,
      go: `params := &stripe.PaymentIntentParams{
  Amount: stripe.Int64(84900),
  Currency: stripe.String(string(stripe.CurrencyEUR)),
  PaymentMethodTypes: stripe.StringSlice([]string{"sepa_debit"}),
  Confirm: stripe.Bool(true),
}
pi, err := paymentintent.New(params)`,
    },
  },
  {
    stepNum: 8,
    stateBadge: 'requires_capture',
    title: 'Manual Authorization Hold (status: requires_capture)',
    endpoint: 'POST /v1/payment_intents (capture_method=manual)',
    sandboxAction: { label: '▶ Run Step 8 in Sandbox: Authorize 7-Day Hold (requires_capture)', action: 'authorize_hold' },
    summary:
      'For custom-built hardware or pre-orders, set `capture_method: "manual"`. After cardholder authentication, Stripe authorizes and reserves `amount_capturable` on the buyer card (`status: requires_capture`, `amount_received: 0`) for up to 7 days (or 30 days with Extended Authorization).',
    clientRole:
      'Identical checkout UX — the buyer sees an authorized hold on their card statement while awaiting warehouse dispatch.',
    serverRole:
      'Verifies warehouse stock and serial number allocation. When ready to ship, triggers `POST /v1/payment_intents/:id/capture` (supports full or partial capture).',
    stripeRole:
      'Maintains the issuer authorization hold (`amount_capturable = 84900`) and warns via webhook before the 7-day hold expiration window.',
    webhookRule:
      'Emits `payment_intent.amount_capturable_updated`. Fulfill warehouse packing on this event, then call `/capture` upon carrier scan.',
    code: {
      curl: `curl https://api.stripe.com/v1/payment_intents \\
  -u sk_test_51Q9...: \\
  -d amount=84900 -d currency=usd \\
  -d capture_method=manual \\
  -d payment_method=pm_card_visa \\
  -d confirm=true`,
      node: `const pi = await stripe.paymentIntents.create({
  amount: 84900,
  currency: 'usd',
  capture_method: 'manual',
  payment_method: 'pm_card_visa',
  confirm: true,
});
// pi.status === 'requires_capture' && pi.amount_capturable === 84900`,
      python: `pi = stripe.PaymentIntent.create(
    amount=84900,
    currency="usd",
    capture_method="manual",
    payment_method="pm_card_visa",
    confirm=True,
)
assert pi.status == "requires_capture"`,
      go: `params := &stripe.PaymentIntentParams{
  Amount: stripe.Int64(84900),
  Currency: stripe.String(string(stripe.CurrencyUSD)),
  CaptureMethod: stripe.String("manual"),
  Confirm: stripe.Bool(true),
}
pi, err := paymentintent.New(params)`,
    },
  },
  {
    stepNum: 9,
    stateBadge: 'succeeded',
    title: 'Capture, Settlement & BalanceTransaction (status: succeeded)',
    endpoint: 'POST /v1/payment_intents/:id/capture',
    sandboxAction: { label: '▶ Run Step 9 in Sandbox: Capture Funds & Settle (succeeded)', action: 'capture_succeed' },
    summary:
      'Terminal success state (`status: succeeded`, `amount_received: 84900`). Whether reached automatically upon confirmation or via manual `/capture`, Stripe creates an immutable `Charge` (`ch_...`), settles a `BalanceTransaction` (`txn_...`), and commits the Stripe Tax transaction.',
    clientRole:
      'Renders the verified receipt with order ID, tax breakdown, and instant digital license activation.',
    serverRole:
      'Verifies the `Stripe-Signature` HMAC-SHA256 header on `payment_intent.succeeded` and provisions hardware shipping + SaaS entitlements.',
    stripeRole:
      'Credits your Stripe Balance (`txn_...`), deducts network interchange + Stripe processing fees, and records the tax transaction (`tax_...`) for automated government filing.',
    webhookRule:
      'Emits `payment_intent.succeeded`, `charge.succeeded`, and `tax.transaction.committed`. Your webhook handler MUST be idempotent by `event.id`.',
    code: {
      curl: `curl https://api.stripe.com/v1/payment_intents/pi_3Q9StateLab.../capture \\
  -u sk_test_51Q9...: \\
  -d amount_to_capture=84900`,
      node: `const capturedPi = await stripe.paymentIntents.capture(
  'pi_3Q9StateLab...',
  { amount_to_capture: 84900 }
);
// capturedPi.status === 'succeeded'`,
      python: `captured_pi = stripe.PaymentIntent.capture(
    "pi_3Q9StateLab...",
    amount_to_capture=84900,
)
assert captured_pi.status == "succeeded"`,
      go: `params := &stripe.PaymentIntentCaptureParams{
  AmountToCapture: stripe.Int64(84900),
}
pi, err := paymentintent.Capture("pi_3Q9StateLab...", params)`,
    },
  },
  {
    stepNum: 10,
    stateBadge: 'connect_and_billing',
    title: 'Connect v2 Split Payouts & Metronome Usage Metering',
    endpoint: 'POST /v2/core/accounts + POST /v1/billing/meter_events',
    sandboxAction: null,
    summary:
      'Immediately after `succeeded`, Stripe orchestrates downstream revenue layers: (1) **Stripe Connect v2** splits marketplace funds via `transfer_group` (retaining your 12% platform fee and routing 88% to partner studios), and (2) **Stripe Billing + Metronome** ingests real-time compute usage (`mtev_...`).',
    clientRole:
      'Displays creator attribution badges and real-time subscription usage meters in the customer portal.',
    serverRole:
      'Creates `Transfer` objects tied to `pi.transfer_group` and streams idempotent `POST /v1/billing/meter_events` payloads as the customer consumes DSP cloud compute.',
    stripeRole:
      'Executes cross-border FX settlement to connected accounts (`acct_2V9...`) and aggregates high-throughput meter events into the customer upcoming invoice.',
    webhookRule:
      'Emits `transfer.created`, `billing.meter_event.ingested`, and `invoice.upcoming` when usage crosses the included tier.',
    code: {
      curl: `# 1. Split payout to Connected Studio:
curl https://api.stripe.com/v1/transfers \\
  -u sk_test_51Q9...: \\
  -d amount=36960 -d currency=usd \\
  -d destination=acct_2V9klangwerkBerlin \\
  -d transfer_group=ORDER_GRP_994810

# 2. Ingest Metronome-powered Billing Meter Event:
curl https://api.stripe.com/v1/billing/meter_events \\
  -u sk_test_51Q9...: \\
  -d event_name=aetheria_neural_dsp_seconds \\
  -d "payload[stripe_customer_id]=cus_Q9AetheriaDemoStudio" \\
  -d "payload[value]=1250"`,
      node: `await stripe.transfers.create({
  amount: 36960,
  currency: 'usd',
  destination: 'acct_2V9klangwerkBerlin',
  transfer_group: paymentIntent.transfer_group,
});

await stripe.billing.meterEvents.create({
  event_name: 'aetheria_neural_dsp_seconds',
  payload: { stripe_customer_id: 'cus_Q9AetheriaDemoStudio', value: '1250' },
});`,
      python: `stripe.Transfer.create(
    amount=36960,
    currency="usd",
    destination="acct_2V9klangwerkBerlin",
    transfer_group=payment_intent.transfer_group,
)
stripe.billing.MeterEvent.create(
    event_name="aetheria_neural_dsp_seconds",
    payload={"stripe_customer_id": "cus_Q9AetheriaDemoStudio", "value": "1250"},
)`,
      go: `tParams := &stripe.TransferParams{
  Amount: stripe.Int64(36960),
  Currency: stripe.String("usd"),
  Destination: stripe.String("acct_2V9klangwerkBerlin"),
}
transfer.New(tParams)`,
    },
  },
  {
    stepNum: 11,
    stateBadge: 'requires_payment_method',
    title: 'Decline Recovery & State Loopback (Revert -> requires_payment_method)',
    endpoint: 'HTTP 402 Card Declined -> Revert to requires_payment_method',
    sandboxAction: { label: '▶ Run Step 11 in Sandbox: Simulate Decline & Loopback', action: 'decline_recover' },
    summary:
      'A critical architectural advantage of Stripe PaymentIntents: when an issuer declines a card (`insufficient_funds`, `expired_card`) or Radar blocks a credential, the intent does NOT die. It **reverts back to `requires_payment_method`** and populates `last_payment_error` so the buyer can retry with a new card or Link wallet on the **same PaymentIntent ID**.',
    clientRole:
      'Reads `error.message` returned by `stripe.confirmPayment()`, keeps the Payment Element open, and prompts the user to select another payment method.',
    serverRole:
      'Does NOT create a new order or new PaymentIntent. Re-uses the existing `pi_...` to guarantee zero duplicate charges.',
    stripeRole:
      'Clears the failed `payment_method` reference, records the structured decline telemetry in `last_payment_error`, and awaits a fresh `pm_...` attachment.',
    webhookRule:
      'Emits `payment_intent.payment_failed`. Inspect `data.object.last_payment_error.decline_code` for automated dunning or Adaptive Acceptance retries.',
    code: {
      curl: `# When confirmation fails with HTTP 402:
# {
#   "id": "pi_3Q9StateLab...",
#   "status": "requires_payment_method",
#   "last_payment_error": {
#     "code": "card_declined",
#     "decline_code": "insufficient_funds"
#   }
# }`,
      node: `const { error } = await stripe.confirmPayment({ elements });
if (error) {
  // PaymentIntent automatically reverted to 'requires_payment_method'
  // Customer can pick Apple Pay, Link, or another card on the SAME client_secret!
  showRetryBanner(error.message, error.decline_code);
}`,
      python: `pi = stripe.PaymentIntent.retrieve("pi_3Q9StateLab...")
if pi.status == "requires_payment_method" and pi.last_payment_error:
    print("Declined:", pi.last_payment_error.decline_code)`,
      go: `pi, _ := paymentintent.Get("pi_3Q9StateLab...", nil)
if pi.LastPaymentError != nil {
  fmt.Println("Retry needed:", pi.LastPaymentError.DeclineCode)
}`,
    },
  },
  {
    stepNum: 12,
    stateBadge: 'canceled_or_refunded',
    title: 'Post-Payment Lifecycle: Void (/cancel), Refunds & Dispute Liability Shift',
    endpoint: 'POST /cancel | POST /v1/refunds | POST /v1/disputes/:id',
    sandboxAction: { label: '▶ Run Step 12 in Sandbox: Simulate Dispute + 3DS2 Liability Shift Win', action: 'dispute_defense' },
    summary:
      'Covers the three terminal post-authorization operations: (1) **Voiding** an uncaptured hold via `/cancel` (`status: canceled`, `$0` interchange fee); (2) **Refunding** a settled charge via `/v1/refunds` with `reverse_transfer=true` to claw back partner splits; and (3) **Dispute Defense** using 3DS2 `CAVV` (`ECI-05`) for automatic chargeback win.',
    clientRole:
      'Displays instant refund confirmation or voided pre-order status in the customer order history.',
    serverRole:
      'Calls `/cancel` if an item is out of stock before capture, or `/v1/refunds` (`reverse_transfer=true`, `refund_application_fee=true`) after capture.',
    stripeRole:
      'Releases card holds immediately on `/cancel`, reverses Connect transfers proportionally on `/v1/refunds`, and submits 3DS2 `CAVV` + Radar evidence to card networks on `charge.dispute.created`.',
    webhookRule:
      'Emits `payment_intent.canceled`, `charge.refunded`, `transfer.reversed`, and `charge.dispute.closed` (`status: won`).',
    code: {
      curl: `# 1. Void an uncaptured hold ($0 processing fee):
curl https://api.stripe.com/v1/payment_intents/pi_3Q9StateLab.../cancel \\
  -u sk_test_51Q9...: \\
  -d cancellation_reason=requested_by_customer

# 2. Refund settled charge + claw back Connect split & platform fee:
curl https://api.stripe.com/v1/refunds \\
  -u sk_test_51Q9...: \\
  -d payment_intent=pi_3Q9StateLab... \\
  -d reverse_transfer=true \\
  -d refund_application_fee=true`,
      node: `// Refund with automatic Connect transfer reversal:
const refund = await stripe.refunds.create({
  payment_intent: 'pi_3Q9StateLab...',
  reverse_transfer: true,
  refund_application_fee: true,
});`,
      python: `refund = stripe.Refund.create(
    payment_intent="pi_3Q9StateLab...",
    reverse_transfer=True,
    refund_application_fee=True,
)`,
      go: `params := &stripe.RefundParams{
  PaymentIntent: stripe.String("pi_3Q9StateLab..."),
  ReverseTransfer: stripe.Bool(true),
  RefundApplicationFee: stripe.Bool(true),
}
r, err := refund.New(params)`,
    },
  },
  {
    stepNum: 13,
    stateBadge: 'bridge_stablecoin',
    title: 'Bridge Stablecoin Payment & Liquidation Address Orchestration (USDC / USDB / EURC)',
    endpoint: 'POST /v1/payment_intents (crypto) + Bridge /v0/liquidation_addresses',
    sandboxAction: { label: '▶ Run Step 13 in Sandbox: Settle via Bridge L2 Stablecoin', action: 'bridge_stablecoin' },
    summary:
      'Powered by Stripe’s acquisition of **Bridge**, merchants accept **USDC**, **USDB**, and **EURC** across Base, Solana, Arbitrum, Polygon, and Stellar as a native Payment Element tab (`payment_method_types: ["crypto"]`). Bridge provisions a deterministic **Liquidation Address** (`br_liq_...`) or EIP-712 Permit2 gasless signature that auto-liquidates incoming stablecoins into your Stripe Fiat Balance (`USD`/`EUR`/`GBP`) or retains native `USDB` in a yield-bearing Stablecoin Financial Account.',
    clientRole:
      'Presents the Bridge Stablecoin selector inside Stripe Payment Element (`crypto.stripe.com` / EIP-6963 wallet connect) with ERC-4337 Paymaster gas sponsorship (`$0.00` ETH/SOL required from the buyer).',
    serverRole:
      'Includes `"crypto"` in `payment_method_types` (or provisions a Bridge `/v0/liquidation_addresses` route) and reconciles settlement via standard `payment_intent.succeeded` webhooks.',
    stripeRole:
      'Bridge monitors L2 block finality (`400ms` on Solana, `~1.5s` on Base), sponsors gas via Paymaster, executes zero-slippage fiat liquidation (`50 bps`), and credits your Stripe `BalanceTransaction` with `0%` chargeback risk.',
    webhookRule:
      'Emits `bridge.liquidation_address.deposit_detected`, `bridge.transfer.completed`, and `payment_intent.succeeded`. Note: Stablecoin refunds return `USDC`/`USDB` directly to the buyer’s originating wallet address.',
    code: {
      curl: `# 1. Accept Stablecoins in Stripe PaymentIntent:
curl https://api.stripe.com/v1/payment_intents \\
  -u sk_test_51Q9...: \\
  -d amount=84900 -d currency=usd \\
  -d "payment_method_types[]=crypto" \\
  -d "payment_method_options[crypto][network]=base" \\
  -d "payment_method_options[crypto][asset]=usdc"

# 2. Provision a Bridge Liquidation Address (Auto-Convert USDC -> Stripe USD):
curl https://api.bridge.xyz/v0/customers/cus_Q9AetheriaDemoStudio/liquidation_addresses \\
  -H "Api-Key: br_live_..." \\
  -d chain=base -d currency=usdc \\
  -d destination_payment_rail=stripe_fiat_balance \\
  -d destination_currency=usd`,
      node: `// 1. Create PaymentIntent with Bridge Stablecoin ('crypto') rail:
const pi = await stripe.paymentIntents.create({
  amount: 84900,
  currency: 'usd',
  payment_method_types: ['card', 'link', 'crypto'],
  payment_method_options: {
    crypto: { network: 'base', asset: 'usdc' },
  },
});

// 2. Or create a persistent Bridge Liquidation Address:
const liqAddress = await bridge.liquidationAddresses.create('cus_Q9AetheriaDemoStudio', {
  chain: 'base',
  currency: 'usdc',
  destination_payment_rail: 'stripe_fiat_balance',
  destination_currency: 'usd',
});`,
      python: `# 1. Stripe PaymentIntent with Bridge Stablecoin support:
pi = stripe.PaymentIntent.create(
    amount=84900,
    currency="usd",
    payment_method_types=["card", "link", "crypto"],
    payment_method_options={"crypto": {"network": "base", "asset": "usdc"}},
)

# 2. Instant cross-border payout via Bridge /v0/transfers:
bridge_transfer = requests.post(
    "https://api.bridge.xyz/v0/transfers",
    headers={"Api-Key": "br_live_...", "Idempotency-Key": "idem_br_01"},
    json={
        "amount": "1250.00",
        "source": {"payment_rail": "stripe_balance", "currency": "usd"},
        "destination": {"payment_rail": "solana", "currency": "usdc", "to_address": "Brdg7xQe..."},
    },
).json()`,
      go: `params := &stripe.PaymentIntentParams{
  Amount: stripe.Int64(84900),
  Currency: stripe.String(string(stripe.CurrencyUSD)),
  PaymentMethodTypes: stripe.StringSlice([]string{"card", "crypto"}),
}
pi, err := paymentintent.New(params)`,
    },
  },
];

function renderStateMachineAcademy() {
  const sidebarEl = document.getElementById('sm-steps-sidebar');
  const detailEl = document.getElementById('sm-detail-card');
  if (!sidebarEl || !detailEl) return;

  sidebarEl.innerHTML = STATE_MACHINE_CURRICULUM.map((item, idx) => {
    const isActive = idx === state.currentSmStep;
    return `
      <button type="button" class="sm-step-btn ${isActive ? 'is-active' : ''}" onclick="openStateMachineStep(${idx})">
        <div class="sm-step-btn__top">
          <span class="sm-step-num">STEP ${String(item.stepNum).padStart(2, '0')}</span>
          <span class="sm-step-state-badge">${item.stateBadge}</span>
        </div>
        <div class="sm-step-title">${item.title}</div>
      </button>
    `;
  }).join('');

  const step = STATE_MACHINE_CURRICULUM[state.currentSmStep] || STATE_MACHINE_CURRICULUM[0];
  const activeCode = step.code[state.smCodeLang] || step.code.curl;

  const livePi = state.smSandboxIntent;
  const liveHistoryHtml = livePi
    ? `
      <div class="summary-ledger" style="margin-top: 1rem;">
        <div class="ledger-row">
          <strong>Live Sandbox PaymentIntent</strong>
          <code class="ledger-mono">${livePi.id} · status: <strong>${livePi.status}</strong></code>
        </div>
        <div class="ledger-row">
          <span>Capturable / Received</span>
          <span class="ledger-mono">Capturable: $${(livePi.amount_capturable / 100).toFixed(2)} · Received: $${(livePi.amount_received / 100).toFixed(2)}</span>
        </div>
        <div style="margin-top: 0.45rem; font-size: 0.75rem; font-family: var(--font-mono); color: var(--ink-secondary);">
          <strong>State Transition Audit Trail:</strong>
          ${(livePi.state_history || [])
            .map((h) => `<div style="margin-top: 0.2rem;">&rarr; [${h.state}] ${h.note}</div>`)
            .join('')}
        </div>
      </div>
    `
    : '';

  detailEl.innerHTML = `
    <div class="surface-panel__header" style="margin-bottom: 1rem;">
      <div>
        <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.35rem;">
          <span class="surface-panel__tag">STEP ${String(step.stepNum).padStart(2, '0')} OF ${STATE_MACHINE_CURRICULUM.length}</span>
          <code style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--accent-cobalt); font-weight: 700;">
            State: ${step.stateBadge}
          </code>
        </div>
        <h3 style="font-size: 1.22rem; font-weight: 700;">${step.title}</h3>
        <div style="font-family: var(--font-mono); font-size: 0.76rem; color: var(--ink-secondary); margin-top: 0.2rem;">
          API Contract: <code>${step.endpoint}</code>
        </div>
      </div>
      ${
        step.sandboxAction
          ? `<button type="button" class="btn btn--cobalt" onclick="executeStateMachineTransition('${step.sandboxAction.action}', ${state.currentSmStep})">
              ${step.sandboxAction.label}
             </button>`
          : ''
      }
    </div>

    <p style="font-size: 0.9rem; color: var(--ink-primary); line-height: 1.6; margin-bottom: 1rem;">
      ${step.summary}
    </p>

    <div class="sm-architecture-grid">
      <div class="sm-arch-box">
        <h4>1. Client (Stripe.js / Elements)</h4>
        <p>${step.clientRole}</p>
      </div>
      <div class="sm-arch-box">
        <h4>2. Merchant Backend Server</h4>
        <p>${step.serverRole}</p>
      </div>
      <div class="sm-arch-box">
        <h4>3. Stripe Core &amp; Card Network</h4>
        <p>${step.stripeRole}</p>
      </div>
      <div class="sm-arch-box">
        <h4>4. Webhook &amp; Idempotency Rule</h4>
        <p>${step.webhookRule}</p>
      </div>
    </div>

    <div style="margin-top: 1.15rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
        <span style="font-family: var(--font-mono); font-size: 0.74rem; font-weight: 700; color: var(--ink-secondary);">
          MULTI-LANGUAGE STRIPE SDK IMPLEMENTATION (${step.endpoint})
        </span>
        <div class="sm-code-tabs">
          <button type="button" class="sm-code-tab ${state.smCodeLang === 'curl' ? 'is-active' : ''}" onclick="selectSmCodeLang('curl')">cURL</button>
          <button type="button" class="sm-code-tab ${state.smCodeLang === 'node' ? 'is-active' : ''}" onclick="selectSmCodeLang('node')">Node.js</button>
          <button type="button" class="sm-code-tab ${state.smCodeLang === 'python' ? 'is-active' : ''}" onclick="selectSmCodeLang('python')">Python</button>
          <button type="button" class="sm-code-tab ${state.smCodeLang === 'go' ? 'is-active' : ''}" onclick="selectSmCodeLang('go')">Go</button>
        </div>
      </div>
      <pre class="sm-code-pre">${activeCode.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
    </div>

    ${liveHistoryHtml}
  `;
}

window.openStateMachineStep = function (stepIndex) {
  state.currentSmStep = stepIndex;
  renderStateMachineAcademy();
};

window.selectSmCodeLang = function (lang) {
  state.smCodeLang = lang;
  renderStateMachineAcademy();
};

window.executeStateMachineTransition = async function (action, targetStepIndex) {
  const currentId = state.smSandboxIntent ? state.smSandboxIntent.id : '';
  const { data } = await fetchJson('/api/stripe/state_machine/step', {
    method: 'POST',
    body: JSON.stringify({
      action: action,
      payment_intent_id: currentId,
    }),
  });

  state.smSandboxIntent = data.payment_intent;
  if (typeof targetStepIndex === 'number') {
    state.currentSmStep = targetStepIndex;
  }

  const badgeEl = document.getElementById('sm-live-pi-badge');
  if (badgeEl && state.smSandboxIntent) {
    badgeEl.textContent = `Active Intent: ${state.smSandboxIntent.id} → status: ${state.smSandboxIntent.status}`;
  }

  if (state.activeView !== 'statemachine') {
    switchView('statemachine');
  } else {
    renderStateMachineAcademy();
  }
  await refreshTelemetryStreams();
};

window.runGuardrailTest = async function (testType, extraParams = {}) {
  const titleEl = document.getElementById('guardrail-result-title');
  const badgeEl = document.getElementById('guardrail-result-badge');
  const jsonEl = document.getElementById('guardrail-result-json');

  const { status, data } = await fetchJson('/api/stripe/guardrails/test', {
    method: 'POST',
    body: JSON.stringify({
      test_type: testType,
      ...extraParams,
    }),
  });

  if (titleEl) {
    titleEl.textContent = data.guardrail || `GUARDRAIL VERIFICATION: ${testType}`;
  }
  if (badgeEl) {
    badgeEl.textContent = data.verdict || `HTTP ${status} VERIFIED`;
  }
  if (jsonEl) {
    jsonEl.textContent = JSON.stringify(data, null, 2);
  }
  await refreshTelemetryStreams();
};

// ==========================================================================
// 8. DEDICATED AGENTIC COMMERCE LOCAL LLM CHATBOT & 6-STEP PIPELINE (VIEW 7)
// ==========================================================================

const DEFAULT_AGENTIC_STEPS_TEMPLATE = [
  {
    step_number: 1,
    step_id: 'intent_and_zero_trust_catalog',
    title: '1. Natural-Language Intent Parsing & Zero-Trust SKU Resolution',
    stripe_primitive: 'Stripe Agentic MCP Catalog Resolver (Zero-Trust Minor Units)',
    endpoint: 'mcp://stripe.agentic/catalog.resolve_skus',
    status: 'idle',
    latency_ms: 0,
    explanation:
      'Parses your natural-language shopping prompt into canonical SKU IDs and quantities. Enforces Best Practice #1 (Zero Trust on Client-Side Amounts): integer minor units are looked up strictly in the server-side CATALOG.',
    curl_snippet: '# Send a natural-language prompt in the chat on the left to execute Step 1',
    request_payload: { waiting_for_prompt: true },
    response_payload: { status: 'ready_for_natural_language_prompt' },
  },
  {
    step_number: 2,
    step_id: 'adaptive_pricing_and_stripe_tax',
    title: '2. Adaptive Pricing FX Quote, Stripe Tax & Connect Split Calculation',
    stripe_primitive: 'Stripe Tax API + Adaptive Pricing FX Quotes + Connect v2 Splits',
    endpoint: 'POST /v1/tax/calculations',
    status: 'idle',
    latency_ms: 0,
    explanation:
      'Calculates local currency presentment via Stripe Adaptive Pricing, validates EU B2B VAT IDs for 0% Reverse Charge, and computes the 12% Platform Fee / 88% Partner Split waterfall.',
    curl_snippet: 'curl https://api.stripe.com/v1/tax/calculations -u sk_test_...:',
    request_payload: {},
    response_payload: {},
  },
  {
    step_number: 3,
    step_id: 'agentic_order_intent_guardrail',
    title: '3. Agentic OrderIntent & Spend Mandate Verification',
    stripe_primitive: 'Stripe Agentic Commerce Toolkit (/v1/agentic/order_intents)',
    endpoint: 'POST /v1/agentic/order_intents',
    status: 'idle',
    latency_ms: 0,
    explanation:
      'Creates an agentic.order_intent (aoi_1Q9...) and verifies that the cart subtotal is within your stated budget ceiling. If the cart exceeds your budget, execution halts before any token is minted.',
    curl_snippet: 'curl https://api.stripe.com/v1/agentic/order_intents -u sk_test_...:',
    request_payload: {},
    response_payload: {},
  },
  {
    step_number: 4,
    step_id: 'delegated_payment_token_mint',
    title: '4. Single-Use Scoped Delegated Payment Token (spt_agent_...)',
    stripe_primitive: 'Visa Agentic Token Service / Stripe Shared Payment Token',
    endpoint: 'POST /v1/agentic/delegated_payment_tokens',
    status: 'idle',
    latency_ms: 0,
    explanation:
      'Provisions a single-use, MCC-locked (5733/5734), amount-capped, 10-minute TTL Delegated Payment Token (spt_agent_1Q9...) so the local LLM agent never touches raw card numbers or private keys.',
    curl_snippet: 'curl https://api.stripe.com/v1/agentic/delegated_payment_tokens -u sk_test_...:',
    request_payload: {},
    response_payload: {},
  },
  {
    step_number: 5,
    step_id: 'idempotent_payment_intent_execution',
    title: '5. Deterministic Idempotent PaymentIntent Execution & Settlement',
    stripe_primitive: 'PaymentIntent API + Single-Call expand[] + Structured Metadata',
    endpoint: 'POST /v1/payment_intents',
    status: 'idle',
    latency_ms: 0,
    explanation:
      'Executes POST /v1/payment_intents using deterministic Idempotency-Key (pi_create_{order_id}_attempt_1), consuming spt_agent_..., hydrating latest_charge.balance_transaction in 1 HTTP call, and settling via Card, Link, or Bridge Stablecoins (USDC/USDB).',
    curl_snippet: 'curl https://api.stripe.com/v1/payment_intents -H "Idempotency-Key: pi_create_..."',
    request_payload: {},
    response_payload: {},
  },
  {
    step_number: 6,
    step_id: 'webhook_dispatch_and_fulfillment',
    title: '6. Signed Webhook Emission (HMAC-SHA256) & Async Fulfillment',
    stripe_primitive: 'Stripe Webhooks (raw_body HMAC-SHA256 + Idempotent Event Queue)',
    endpoint: 'POST /api/stripe/webhooks/receive',
    status: 'idle',
    latency_ms: 0,
    explanation:
      'Emits cryptographically signed webhooks (agentic.order_intent.created, payment_intent.succeeded, transfer.created) and syncs the completed order into the store ledger.',
    curl_snippet: '# Verified via stripe.Webhook.construct_event(raw_body, sig_header, whsec_...)',
    request_payload: {},
    response_payload: {},
  },
];

function renderAgenticStepsPipeline() {
  const listEl = document.getElementById('agentic-steps-list');
  const inspectorEl = document.getElementById('agentic-step-inspector');
  if (!listEl || !inspectorEl) return;

  const steps =
    state.agenticStepsTrace && state.agenticStepsTrace.length > 0
      ? state.agenticStepsTrace
      : DEFAULT_AGENTIC_STEPS_TEMPLATE;

  listEl.innerHTML = steps
    .map((step, idx) => {
      const isSelected = idx === state.selectedAgenticStepIndex;
      const statusKey = step.status || 'idle';
      const statusLabelMap = {
        completed: '✓ Completed',
        awaiting_human_approval: '⏸ Awaiting Human Approval',
        blocked_by_guardrail: '🛑 Blocked by Guardrail',
        skipped: '— Skipped',
        idle: '○ Ready',
      };
      const statusLabel = statusLabelMap[statusKey] || statusKey;
      const latencyText = step.latency_ms ? ` · ${step.latency_ms}ms` : '';
      return `
        <button type="button" class="agentic-step-card ${isSelected ? 'is-selected' : ''}" onclick="selectAgenticStep(${idx})">
          <div class="agentic-step-card__top">
            <span>STEP 0${step.step_number} · <code>${step.stripe_primitive}</code></span>
            <span class="step-status-pill step-status-pill--${statusKey}">${statusLabel}${latencyText}</span>
          </div>
          <div class="agentic-step-card__title">${step.title}</div>
          <div class="agentic-step-card__endpoint">Endpoint: <code>${step.endpoint}</code></div>
        </button>
      `;
    })
    .join('');

  const activeStep = steps[state.selectedAgenticStepIndex] || steps[0];
  inspectorEl.innerHTML = `
    <div style="border-bottom: 1px solid hsla(210, 15%, 85%, 0.18); padding-bottom: 0.55rem; margin-bottom: 0.65rem; display: flex; justify-content: space-between; align-items: center;">
      <strong style="color: hsl(195, 85%, 72%);">STEP 0${activeStep.step_number} INSPECTOR: ${activeStep.title}</strong>
      <span style="color: hsl(154, 75%, 65%);">${(activeStep.status || 'idle').toUpperCase()}</span>
    </div>
    <div style="color: hsl(210, 20%, 92%); margin-bottom: 0.75rem; font-family: var(--font-sans); font-size: 0.81rem; line-height: 1.5;">
      ${activeStep.explanation}
    </div>
    <div style="color: hsl(42, 90%, 72%); font-size: 0.7rem; margin-bottom: 0.25rem;">/* Equivalent cURL / SDK Call */</div>
    <pre style="margin: 0 0 0.75rem 0; padding: 0.6rem; background: hsl(210, 22%, 7%); border-radius: 4px; overflow-x: auto; color: hsl(195, 55%, 88%);">${(activeStep.curl_snippet || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
    <div style="color: hsl(42, 90%, 72%); font-size: 0.7rem; margin-bottom: 0.25rem;">/* Tool Request Payload */</div>
    <pre style="margin: 0 0 0.75rem 0; padding: 0.6rem; background: hsl(210, 22%, 7%); border-radius: 4px; overflow-x: auto; color: hsl(210, 20%, 88%);">${JSON.stringify(activeStep.request_payload, null, 2)}</pre>
    <div style="color: hsl(154, 75%, 65%); font-size: 0.7rem; margin-bottom: 0.25rem;">/* Live Stripe Agentic Response */</div>
    <pre style="margin: 0; padding: 0.6rem; background: hsl(210, 22%, 7%); border-radius: 4px; overflow-x: auto; color: hsl(154, 65%, 86%);">${JSON.stringify(activeStep.response_payload, null, 2)}</pre>
  `;
}

window.toggleAgenticPopup = function (forceOpen) {
  const widget = document.getElementById('agentic-popup-widget');
  const launcher = document.getElementById('agentic-popup-launcher');
  const navBtn = document.getElementById('tab-btn-agentic-chat');
  if (!widget) return;

  const isCurrentlyOpen = widget.classList.contains('is-open');
  const nextOpen = typeof forceOpen === 'boolean' ? forceOpen : !isCurrentlyOpen;

  widget.classList.toggle('is-open', nextOpen);
  if (launcher) {
    launcher.classList.toggle('is-open', nextOpen);
    launcher.setAttribute('aria-expanded', String(nextOpen));
  }
  if (navBtn) {
    navBtn.classList.toggle('is-active', nextOpen);
  }
  if (nextOpen) {
    renderAgenticStepsPipeline();
    const inputEl = document.getElementById('input-agentic-chat-prompt');
    if (inputEl) {
      setTimeout(() => inputEl.focus(), 80);
    }
  }
};

window.toggleAgenticPopupConfig = function () {
  const drawer = document.getElementById('agentic-popup-config-drawer');
  if (!drawer) return;
  drawer.classList.toggle('is-open');
};

window.toggleAgenticPopupTrace = function (forceShow) {
  const widget = document.getElementById('agentic-popup-widget');
  const btn = document.getElementById('btn-toggle-agentic-trace');
  if (!widget) return;
  const isCompact =
    typeof forceShow === 'boolean' ? !forceShow : !widget.classList.contains('is-compact-trace');
  widget.classList.toggle('is-compact-trace', isCompact);
  if (btn) {
    btn.textContent = isCompact ? '🔍 Show 6-Step Trace' : '🔍 Hide 6-Step Trace';
  }
};

window.toggleAgenticPopupMaximize = function () {
  const widget = document.getElementById('agentic-popup-widget');
  const btn = document.getElementById('btn-maximize-agentic-popup');
  if (!widget) return;
  const isMax = widget.classList.toggle('is-maximized');
  if (btn) {
    btn.textContent = isMax ? '🗗 Restore Size' : '⤢ Maximize';
  }
};

window.selectAgenticStep = function (index) {
  state.selectedAgenticStepIndex = index;
  window.toggleAgenticPopupTrace(true);
  renderAgenticStepsPipeline();
};

function formatSimpleMarkdownBold(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function appendAgenticChatMessage(role, htmlContent) {
  const feed = document.getElementById('agentic-chat-messages');
  if (!feed) return;
  const wrapper = document.createElement('div');
  wrapper.className = `chat-msg chat-msg--${role}`;
  const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const senderLabel = role === 'user' ? 'You (Buyer Mandate)' : 'Aetheria Local LLM Agent';
  const subLabel = role === 'user' ? 'Natural Language Prompt' : 'Stripe ACP + MCP Tool Executor';
  wrapper.innerHTML = `
    <div class="chat-msg__meta">
      <strong>${senderLabel}</strong>
      <span>${subLabel} · ${nowStr}</span>
    </div>
    <div class="chat-msg__bubble">${htmlContent}</div>
  `;
  feed.appendChild(wrapper);
  feed.scrollTop = feed.scrollHeight;
}

window.sendAgenticQuickPrompt = function (promptText) {
  const inputEl = document.getElementById('input-agentic-chat-prompt');
  if (inputEl) {
    inputEl.value = promptText;
  }
  executeAgenticChatTurn(promptText);
};

window.handleAgenticChatSubmit = function (event) {
  if (event) event.preventDefault();
  const inputEl = document.getElementById('input-agentic-chat-prompt');
  if (!inputEl) return;
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = '';
  executeAgenticChatTurn(text);
};

async function executeAgenticChatTurn(promptText) {
  appendAgenticChatMessage('user', formatSimpleMarkdownBold(promptText));

  const execMode = document.getElementById('select-agent-exec-mode')?.value || 'auto_complete';
  const railOverride = document.getElementById('select-agent-rail-override')?.value || 'auto';
  const budgetVal = parseFloat(document.getElementById('input-agent-budget-override')?.value || '');
  const llmRuntime = document.getElementById('select-agent-llm-runtime')?.value || 'builtin';

  const statusBadge = document.getElementById('agentic-trace-status-badge');
  if (statusBadge) {
    statusBadge.textContent = 'Executing 6-Step ACP Pipeline...';
  }

  const { data } = await fetchJson('/api/stripe/agentic/chat', {
    method: 'POST',
    body: JSON.stringify({
      message: promptText,
      locale: state.currentLocale,
      execution_mode: execMode,
      payment_rail_override: railOverride,
      budget_override_usd: !isNaN(budgetVal) && budgetVal > 0 ? budgetVal : null,
      try_ollama: llmRuntime === 'ollama',
    }),
  });

  const engineBadge = document.getElementById('agentic-llm-engine-badge');
  if (engineBadge && data.llm_engine) {
    engineBadge.textContent = `● ${data.llm_engine}`;
  }

  // Animate step-by-step trace progression so the user sees each step light up
  const fullSteps = data.steps || [];
  state.agenticStepsTrace = fullSteps;
  for (let i = 0; i < fullSteps.length; i++) {
    state.selectedAgenticStepIndex = i;
    renderAgenticStepsPipeline();
    // Brief visual step highlight delay (75ms per step)
    await new Promise((r) => setTimeout(r, 75));
  }

  // Focus on the most relevant step (Step 3 if blocked, Step 4/5 if awaiting human, Step 5 if succeeded)
  if (data.status === 'blocked_by_budget_guardrail') {
    state.selectedAgenticStepIndex = 2;
  } else if (data.status === 'requires_human_confirmation') {
    state.selectedAgenticStepIndex = 4;
  } else {
    state.selectedAgenticStepIndex = 4;
  }
  renderAgenticStepsPipeline();

  if (statusBadge) {
    statusBadge.textContent = `Pipeline Status: ${data.status.toUpperCase()}`;
  }

  // Build rich receipt / action card inside the assistant chat bubble
  let extraCardHtml = '';
  const calc = data.calculation;
  const oi = data.order_intent;
  const dpt = data.delegated_payment_token;
  const pi = data.payment_intent;

  if (data.status === 'blocked_by_budget_guardrail' && oi) {
    extraCardHtml = `
      <div class="chat-receipt-card" style="border-color: hsl(0, 70%, 80%); background: var(--accent-crimson-soft);">
        <div class="ledger-row"><strong>🛑 SPEND GUARDRAIL TRIGGERED (STEP 3)</strong><code>${oi.id}</code></div>
        <div class="ledger-row"><span>Cart Subtotal vs Mandate Ceiling:</span><strong>$${(oi.cart_subtotal_usd_cents / 100).toFixed(2)} USD &gt; $${(oi.budget_ceiling_usd_cents / 100).toFixed(2)} USD</strong></div>
        <div class="ledger-row"><span>Delegated Token Minted:</span><code>NONE (Halted Safely)</code></div>
      </div>
    `;
  } else if (data.status === 'requires_human_confirmation' && oi && dpt) {
    extraCardHtml = `
      <div class="chat-receipt-card">
        <div class="ledger-row"><strong>⏸ AWAITING HUMAN APPROVAL</strong><code>${oi.id}</code></div>
        <div class="ledger-row"><span>Scoped Single-Use Token:</span><code style="color: var(--accent-cobalt);">${dpt.id} (${dpt.rail})</code></div>
        <div class="ledger-row"><span>Cryptographic Spend Cap:</span><strong>${calc.formatted.total} (${dpt.max_amount} minor units · MCC 5733/5734)</strong></div>
        <div style="margin-top: 0.45rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <button type="button" class="btn btn--link-green" onclick="confirmPendingAgenticOrder('${oi.id}')">
            ✓ Approve &amp; Execute PaymentIntent (${calc.formatted.total})
          </button>
          <button type="button" class="btn" onclick="selectAgenticStep(3)">
            🔍 Inspect spt_agent_ Token (Step 4)
          </button>
        </div>
      </div>
    `;
  } else if (pi && dpt) {
    const bt = pi.latest_charge && typeof pi.latest_charge === 'object' ? pi.latest_charge.balance_transaction : null;
    const br = pi.bridge_stablecoin_details;
    extraCardHtml = `
      <div class="chat-receipt-card">
        <div class="ledger-row"><strong>✓ AGENTIC PURCHASE SUCCEEDED</strong><code style="color: var(--accent-link-green);">${pi.id}</code></div>
        <div class="ledger-row"><span>OrderIntent &amp; Single-Use Token:</span><code>${oi.id} &rarr; ${dpt.id}</code></div>
        <div class="ledger-row"><span>Deterministic Idempotency-Key:</span><code>${pi.idempotency_protection.idempotency_key}</code></div>
        <div class="ledger-row"><span>Total Settled (${pi.currency.toUpperCase()}):</span><strong>${calc.formatted.total} (Tax: ${calc.formatted.tax}${calc.is_eu_reverse_charge ? ' · 0% Reverse Charge' : ''})</strong></div>
        ${bt ? `<div class="ledger-row"><span>Expanded BalanceTxn (1-Call):</span><code>${bt.id} · Net: ${formatMinorUnitsDirect(bt.net, calc.locale)} · Fee: ${formatMinorUnitsDirect(bt.fee, calc.locale)}</code></div>` : ''}
        ${br ? `<div class="ledger-row" style="color: var(--accent-cobalt);"><span>Bridge Stablecoin L2 Settlement:</span><code>${br.stablecoin_amount_paid} on ${br.source_chain.toUpperCase()} (${br.finality_ms}ms)</code></div>` : ''}
        <div style="margin-top: 0.4rem; display: flex; gap: 0.45rem; flex-wrap: wrap;">
          <button type="button" class="btn" style="padding: 0.25rem 0.55rem; font-size: 0.7rem;" onclick="selectAgenticStep(4)">
            🔍 Inspect Step 5 PaymentIntent JSON
          </button>
          <button type="button" class="btn" style="padding: 0.25rem 0.55rem; font-size: 0.7rem;" onclick="switchView('checkout')">
            🛒 View in Optimized Checkout
          </button>
        </div>
      </div>
    `;

    // Sync store cart & latestPaymentIntent so Checkout tab reflects the agent's purchase
    if (data.parsed_intent && Array.isArray(data.parsed_intent.selected_items)) {
      state.cart = data.parsed_intent.selected_items;
      updateCartBadges();
    }
    state.latestPaymentIntent = pi;
  }

  appendAgenticChatMessage('agent', `${formatSimpleMarkdownBold(data.assistant_message)}${extraCardHtml}`);
  await refreshTelemetryStreams();
}

window.confirmPendingAgenticOrder = async function (orderIntentId) {
  const llmRuntime = document.getElementById('select-agent-llm-runtime')?.value || 'builtin';
  const { status, data } = await fetchJson('/api/stripe/agentic/confirm_order', {
    method: 'POST',
    body: JSON.stringify({
      order_intent_id: orderIntentId,
      try_ollama: llmRuntime === 'ollama',
    }),
  });

  if (status !== 200 || !data.payment_intent) {
    appendAgenticChatMessage('agent', `⚠️ Could not confirm OrderIntent <code>${orderIntentId}</code>: ${data.error?.message || 'Unknown error'}`);
    return;
  }

  // Replace Steps 5 & 6 in state.agenticStepsTrace with the completed steps
  if (Array.isArray(data.steps_5_and_6) && state.agenticStepsTrace.length >= 4) {
    state.agenticStepsTrace = [
      ...state.agenticStepsTrace.slice(0, 4),
      ...data.steps_5_and_6,
    ];
    state.selectedAgenticStepIndex = 4;
    renderAgenticStepsPipeline();
  }

  const statusBadge = document.getElementById('agentic-trace-status-badge');
  if (statusBadge) {
    statusBadge.textContent = 'Pipeline Status: SUCCEEDED';
  }

  const pi = data.payment_intent;
  const calc = data.calculation;
  const dpt = data.delegated_payment_token;
  const bt = pi.latest_charge && typeof pi.latest_charge === 'object' ? pi.latest_charge.balance_transaction : null;

  const receiptHtml = `
    <div class="chat-receipt-card">
      <div class="ledger-row"><strong>✓ HUMAN-APPROVED PAYMENT_INTENT SUCCEEDED</strong><code style="color: var(--accent-link-green);">${pi.id}</code></div>
      <div class="ledger-row"><span>Consumed Single-Use Token:</span><code>${dpt.id}</code></div>
      <div class="ledger-row"><span>Deterministic Idempotency-Key:</span><code>${pi.idempotency_protection.idempotency_key}</code></div>
      <div class="ledger-row"><span>Total Settled:</span><strong>${calc.formatted.total}</strong></div>
      ${bt ? `<div class="ledger-row"><span>Expanded BalanceTxn (1-Call):</span><code>${bt.id} · Net: ${formatMinorUnitsDirect(bt.net, calc.locale)}</code></div>` : ''}
    </div>
  `;

  state.latestPaymentIntent = pi;
  appendAgenticChatMessage('agent', `${formatSimpleMarkdownBold(data.assistant_message)}${receiptHtml}`);
  await refreshTelemetryStreams();
};

document.addEventListener('DOMContentLoaded', initApp);


