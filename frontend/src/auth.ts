import type Keycloak from 'keycloak-js'
import type { KeycloakConfig } from 'keycloak-js'

export type AuthStatus = 'loading' | 'anonymous' | 'authenticated' | 'redirecting' | 'error'
export interface Session {
  readonly status: AuthStatus
  readonly name: string
  readonly subject: string
  readonly error: string
}
export interface SessionAuth {
  getToken(force?: boolean): Promise<string>
  invalidate(message?: string): void
}
export type AuthClient = Pick<Keycloak,
  'init' | 'login' | 'logout' | 'updateToken' | 'clearToken' | 'authenticated' |
  'token' | 'tokenParsed' | 'onAuthLogout' | 'onAuthRefreshError' | 'onTokenExpired'>

export class SessionError extends Error {
  constructor() { super('로그인이 만료되었습니다. 다시 로그인해 주세요.') }
}

export function createAuth({
  fetch: fetcher = globalThis.fetch.bind(globalThis),
  loadClient = async (config: KeycloakConfig): Promise<AuthClient> => {
    const { default: Client } = await import('keycloak-js')
    return new Client(config)
  },
  redirectUri = globalThis.location.origin + globalThis.location.pathname,
  onChange,
}: {
  fetch?: typeof fetch
  loadClient?: (config: KeycloakConfig) => Promise<AuthClient>
  redirectUri?: string
  onChange: (session: Session) => void
}) {
  let client: AuthClient | undefined
  let version = 0
  let status: AuthStatus = 'loading'

  function publish(next: AuthStatus, error = '') {
    status = next
    const claims = next === 'authenticated' ? client?.tokenParsed : undefined
    onChange({
      status, error, subject: claims?.sub || '',
      name: claims?.name || claims?.preferred_username || claims?.sub || '',
    })
  }
  function invalidate(message = new SessionError().message) {
    version++
    publish('anonymous', message)
    client?.clearToken()
  }
  async function getToken(force = false) {
    if (status !== 'authenticated' || !client) throw new SessionError()
    const current = version
    try {
      await client.updateToken(force ? -1 : 30)
      if (current !== version || !client.authenticated || !client.token) throw new SessionError()
      return client.token
    } catch {
      if (current === version) invalidate()
      throw new SessionError()
    }
  }
  return {
    getToken,
    invalidate,
    async init() {
      const current = ++version
      publish('loading')
      try {
        const response = await fetcher('/api/auth/config', {cache: 'no-store'})
        if (!response.ok) throw new SessionError()
        const config: unknown = await response.json()
        if (!config || typeof config !== 'object' ||
            !('url' in config) || typeof config.url !== 'string' || !config.url ||
            !('realm' in config) || typeof config.realm !== 'string' || !config.realm ||
            !('clientId' in config) || typeof config.clientId !== 'string' || !config.clientId) {
          throw new SessionError()
        }
        const next = await loadClient({url: config.url, realm: config.realm, clientId: config.clientId})
        if (current !== version) return
        client = next
        next.onAuthLogout = () => { if (status === 'authenticated') invalidate() }
        next.onAuthRefreshError = () => { if (status === 'authenticated') invalidate() }
        next.onTokenExpired = () => {
          if (status === 'authenticated') void getToken().catch((error: unknown) => {
            if (!(error instanceof SessionError)) throw error
          })
        }
        const authenticated = await next.init({
          onLoad: 'check-sso', flow: 'standard', pkceMethod: 'S256',
          responseMode: 'fragment', redirectUri, logoutMethod: 'POST',
        })
        if (current === version) publish(authenticated ? 'authenticated' : 'anonymous')
      } catch {
        if (current === version) publish('error', '인증 서버에 연결하지 못했습니다. 다시 시도해 주세요.')
      }
    },
    async login() {
      if (!client || status !== 'anonymous') return
      publish('redirecting')
      try { await client.login({redirectUri}) }
      catch { publish('error', '로그인 화면을 열지 못했습니다. 다시 시도해 주세요.') }
    },
    async logout() {
      const previous = client
      version++
      publish('anonymous')
      try { await previous?.logout({redirectUri, logoutMethod: 'POST'}) }
      catch { publish('anonymous', '로그아웃 연결에 실패했습니다. 다시 로그인해 주세요.') }
      finally { previous?.clearToken() }
    },
  }
}
