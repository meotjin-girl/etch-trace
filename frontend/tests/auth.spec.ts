import { expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createAuth, SessionError, type AuthClient, type Session } from '@/auth'
import { useIdentityStore } from '@/stores/identity'
import { useInvestigationStore } from '@/stores/investigation'
import { useRecordsStore } from '@/stores/records'
import type { Task } from '@/api/types'

function setup(authenticated = true) {
  const states: Session[] = []
  const adapter: AuthClient = {
    authenticated, token: 'access-token',
    tokenParsed: {sub:'account-1', preferred_username:'teammate'},
    init: vi.fn(async () => authenticated),
    login: vi.fn(async () => {}),
    logout: vi.fn(async () => {}),
    updateToken: vi.fn(async () => false),
    clearToken: vi.fn(() => { adapter.token = undefined; adapter.authenticated = false }),
  }
  const loadClient = vi.fn(async () => adapter)
  const session = createAuth({
    fetch:async () => new Response(JSON.stringify({
      url:'http://localhost:8080/auth', realm:'trace', clientId:'trace-web',
    })),
    loadClient, redirectUri:'http://localhost:8080/records/one',
    onChange:state => states.push(state),
  })
  return {session, adapter, states, loadClient}
}

test('authentication initializes PKCE and publishes account identity from adapter claims', async () => {
  const {session, adapter, states, loadClient} = setup()
  await session.init()
  expect(loadClient).toHaveBeenCalledWith({
    url:'http://localhost:8080/auth', realm:'trace', clientId:'trace-web',
  })
  expect(adapter.init).toHaveBeenCalledWith(expect.objectContaining({
    onLoad:'check-sso', flow:'standard', pkceMethod:'S256', responseMode:'fragment',
  }))
  expect(states.at(-1)).toMatchObject({status:'authenticated', subject:'account-1', name:'teammate'})
  expect(await session.getToken()).toBe('access-token')
  expect(adapter.updateToken).toHaveBeenCalledWith(30)
})

test('anonymous session can open login but cannot obtain an access token', async () => {
  const {session, adapter, states} = setup(false)
  await session.init()
  await expect(session.getToken()).rejects.toBeInstanceOf(SessionError)
  await session.login()
  expect(adapter.login).toHaveBeenCalledOnce()
  expect(states.at(-1)?.status).toBe('redirecting')
})

test('refresh failure clears session and adapter tokens', async () => {
  const {session, adapter, states} = setup()
  await session.init()
  adapter.updateToken = vi.fn(async () => { throw new Error('expired') })
  await expect(session.getToken()).rejects.toBeInstanceOf(SessionError)
  expect(states.at(-1)).toMatchObject({status:'anonymous', subject:'', name:''})
  expect(adapter.clearToken).toHaveBeenCalledOnce()
})

test('logout invalidates UI before redirect and clears tokens afterward', async () => {
  const {session, adapter, states} = setup()
  await session.init()
  adapter.logout = vi.fn(async () => {
    expect(states.at(-1)?.status).toBe('anonymous')
    expect(adapter.token).toBe('access-token')
  })
  await session.logout()
  expect(adapter.logout).toHaveBeenCalledWith({
    redirectUri:'http://localhost:8080/records/one', logoutMethod:'POST',
  })
  expect(adapter.token).toBeUndefined()
})

test('late token renewal cannot resurrect an invalidated login', async () => {
  const {session, adapter, states} = setup()
  await session.init()
  const renewal = Promise.withResolvers<boolean>()
  adapter.updateToken = () => renewal.promise
  const pending = session.getToken()
  session.invalidate()
  renewal.resolve(true)
  await expect(pending).rejects.toBeInstanceOf(SessionError)
  expect(states.at(-1)?.status).toBe('anonymous')
})

test('logout clears in-flight workspace state before navigation', async () => {
  setActivePinia(createPinia())
  const identity = useIdentityStore()
  identity.status = 'authenticated'
  identity.name = 'teammate'
  identity.subject = 'account-1'
  const investigation = useInvestigationStore()
  const records = useRecordsStore()
  investigation.task = {id:'old', status:'WAITING_INPUT'}
  investigation.draft = 'private draft'
  records.records = [{id:'old', status:'WAITING_INPUT'}]
  await identity.logout()
  expect(identity.status).toBe('anonymous')
  expect(identity.subject).toBe('')
  expect(investigation.task).toBeNull()
  expect(investigation.draft).toBe('')
  expect(records.records).toEqual([])
})

test('a list response already in flight cannot restore records after logout', async () => {
  setActivePinia(createPinia())
  const identity = useIdentityStore()
  identity.status = 'authenticated'
  const response = Promise.withResolvers<Task[]>()
  identity.api.list = () => response.promise
  const records = useRecordsStore()
  const pending = records.refresh()
  await identity.logout()
  response.resolve([{id:'previous-session', status:'DONE'}])
  await pending
  expect(records.records).toEqual([])
  expect(records.refreshing).toBe(false)
})
