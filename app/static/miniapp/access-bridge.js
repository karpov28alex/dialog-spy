const nativeFetch = window.fetch.bind(window);
let cachedDecision = null;
let cachedAt = 0;

async function loadDecision(options = {}) {
  const now = Date.now();
  if (cachedDecision && now - cachedAt < 3000) return cachedDecision;
  const response = await nativeFetch('/api/v3/access', {
    ...options,
    cache: 'no-store',
    headers: {...(options.headers || {})},
  });
  if (!response.ok) return null;
  cachedDecision = await response.json();
  cachedAt = now;
  window.__phantomAccess = cachedDecision;
  return cachedDecision;
}

function mergeAccess(me, decision) {
  if (!decision || !me || typeof me !== 'object') return me;
  const state = decision.state;
  me.platform_access = decision;
  me.access = {
    ...(me.access || {}),
    active: Boolean(decision.allowed),
    ends_at: decision.valid_until || me.access?.ends_at || null,
    needs_payment: ['referral_required', 'payment_required'].includes(state),
  };
  me.funnel = {
    ...(me.funnel || {}),
    enabled: true,
    channel_verified: state !== 'channel_required',
  };
  me.business_connected = state !== 'business_required' && state !== 'channel_required';
  return me;
}

window.fetch = async function platformAccessFetch(input, options = {}) {
  const url = typeof input === 'string' ? input : input?.url || '';
  const response = await nativeFetch(input, options);
  if (!response.ok || !url.includes('/api/me')) return response;

  try {
    const me = await response.clone().json();
    const decision = await loadDecision(options);
    const body = JSON.stringify(mergeAccess(me, decision));
    return new Response(body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch {
    return response;
  }
};

window.addEventListener('phantom:access:refresh', () => {
  cachedDecision = null;
  cachedAt = 0;
});
