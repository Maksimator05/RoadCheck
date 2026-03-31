import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { apiRequest } from '../lib/api'
import type { AuthTokens, TokenResponse, User } from '../types/api'

interface Credentials {
  email: string
  password: string
}

interface AuthContextValue {
  tokens: AuthTokens | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (credentials: Credentials) => Promise<void>
  register: (credentials: Credentials) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<User | null>
}

const STORAGE_KEY = 'roadcheck.auth'

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function readStoredTokens(): AuthTokens | null {
  const rawValue = localStorage.getItem(STORAGE_KEY)

  if (!rawValue) {
    return null
  }

  try {
    return JSON.parse(rawValue) as AuthTokens
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

function writeStoredTokens(tokens: AuthTokens | null) {
  if (!tokens) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens))
}

function mapTokens(response: TokenResponse): AuthTokens {
  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<AuthTokens | null>(() => readStoredTokens())
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isCancelled = false

    async function syncCurrentUser() {
      if (!tokens?.accessToken) {
        setUser(null)
        setIsLoading(false)
        return
      }

      setIsLoading(true)

      try {
        const profile = await apiRequest<User>('/profile/me', {
          token: tokens.accessToken,
        })

        if (!isCancelled) {
          setUser(profile)
        }
      } catch {
        writeStoredTokens(null)
        if (!isCancelled) {
          setTokens(null)
          setUser(null)
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void syncCurrentUser()

    return () => {
      isCancelled = true
    }
  }, [tokens?.accessToken])

  async function applyAuthResponse(
    endpoint: '/auth/login' | '/auth/register',
    credentials: Credentials
  ) {
    const response = await apiRequest<TokenResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify(credentials),
    })

    const nextTokens = mapTokens(response)
    writeStoredTokens(nextTokens)
    setTokens(nextTokens)
  }

  async function login(credentials: Credentials) {
    await applyAuthResponse('/auth/login', credentials)
  }

  async function register(credentials: Credentials) {
    await applyAuthResponse('/auth/register', credentials)
  }

  async function logout() {
    const refreshToken = tokens?.refreshToken

    try {
      if (refreshToken) {
        await apiRequest<void>('/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: refreshToken }),
          responseType: 'void',
        })
      }
    } finally {
      writeStoredTokens(null)
      setTokens(null)
      setUser(null)
      setIsLoading(false)
    }
  }

  async function refreshUser() {
    if (!tokens?.accessToken) {
      return null
    }

    const profile = await apiRequest<User>('/profile/me', {
      token: tokens.accessToken,
    })

    setUser(profile)
    return profile
  }

  return (
    <AuthContext.Provider
      value={{
        tokens,
        user,
        isAuthenticated: Boolean(tokens?.accessToken),
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuthContext must be used inside AuthProvider')
  }

  return context
}
