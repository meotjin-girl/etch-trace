export function createAuth({
  fetch: fetcher = globalThis.fetch.bind(globalThis),
  loadKeycloak = () => import('/vendor/keycloak.js'),
  redirectUri = globalThis.location?.origin + globalThis.location?.pathname,
  onChange = () => {}
} = {}) {
  let client;
  let version = 0;
  let session = {status:'loading', name:'', error:''};
  const publish = (status, error = '') => {
    session = {status, error, name:status === 'authenticated' ?
      client.tokenParsed?.name || client.tokenParsed?.preferred_username || client.tokenParsed?.sub || '' : ''};
    onChange(session);
  };
  function invalidate(message = '로그인이 만료되었습니다. 다시 로그인해 주세요.') {
    version++;
    const previous = client;
    publish('anonymous', message);
    previous?.clearToken();
  }
  async function getToken() {
    if (session.status !== 'authenticated') throw new Error('로그인이 필요합니다.');
    const current = version;
    try {
      await client.updateToken(30);
      if (current !== version || !client.authenticated || !client.token) throw new Error('Session expired');
      return client.token;
    } catch {
      if (current === version) invalidate();
      throw new Error('로그인이 만료되었습니다. 다시 로그인해 주세요.');
    }
  }
  return {
    get session() { return session; },
    getToken,
    invalidate,
    async init() {
      const current = ++version;
      publish('loading');
      try {
        const response = await fetcher('/api/auth/config', {cache:'no-store'});
        if (!response.ok) throw new Error('인증 설정을 불러오지 못했습니다.');
        const {url, realm, clientId} = await response.json();
        if (![url, realm, clientId].every(value => typeof value === 'string' && value)) {
          throw new Error('인증 설정이 올바르지 않습니다.');
        }
        const {default:Keycloak} = await loadKeycloak();
        if (current !== version) return;
        client = new Keycloak({url, realm, clientId});
        client.onAuthLogout = () => {
          if (session.status === 'authenticated') invalidate();
        };
        client.onAuthRefreshError = () => {
          if (session.status === 'authenticated') invalidate();
        };
        client.onTokenExpired = () => {
          if (session.status === 'authenticated') getToken().catch(() => {});
        };
        const authenticated = await client.init({
          onLoad:'check-sso', flow:'standard', pkceMethod:'S256',
          responseMode:'fragment', redirectUri, logoutMethod:'POST'
        });
        if (current === version) publish(authenticated ? 'authenticated' : 'anonymous');
      } catch {
        if (current === version) publish('error', '인증 서버에 연결하지 못했습니다. 다시 시도해 주세요.');
      }
    },
    async login() {
      if (!client || session.status !== 'anonymous') return;
      publish('redirecting');
      try { await client.login({redirectUri}); }
      catch { publish('error', '로그인 화면을 열지 못했습니다. 다시 시도해 주세요.'); }
    },
    async logout() {
      const previous = client;
      version++;
      // Invalidate the workspace before navigation while preserving the ID token
      // just long enough for the adapter's POST logout form.
      publish('anonymous');
      try { await previous?.logout({redirectUri, logoutMethod:'POST'}); }
      catch { publish('anonymous', '로그아웃 연결에 실패했습니다. 다시 로그인해 주세요.'); }
      finally { previous?.clearToken(); }
    }
  };
}
