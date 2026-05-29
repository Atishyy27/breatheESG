import { createContext, useContext, useState, useEffect } from 'react'

export type Role = 'ANALYST' | 'AUDITOR' | 'MANAGER' | 'CFO'

interface RoleInfo {
  id: Role
  label: string
  description: string
  icon: string
  canUpload: boolean
  canApprove: boolean
  canBatchApprove: boolean
  canExport: boolean
  canViewRaw: boolean
  showFinancialContext: boolean
  routes: string[]
}

export const ROLES: Record<Role, RoleInfo> = {
  ANALYST: {
    id: 'ANALYST',
    label: 'Sustainability Analyst',
    description: 'Reviews and approves individual emission records. Full access to raw data and validation details.',
    icon: '🔬',
    canUpload: true,
    canApprove: true,
    canBatchApprove: false,
    canExport: true,
    canViewRaw: true,
    showFinancialContext: false,
    routes: ['/', '/review', '/uploads', '/analytics', '/audit'],
  },
  AUDITOR: {
    id: 'AUDITOR',
    label: 'External Auditor',
    description: 'Read-only access to approved records and full audit trail. Cannot modify data.',
    icon: '📋',
    canUpload: false,
    canApprove: false,
    canBatchApprove: false,
    canExport: true,
    canViewRaw: true,
    showFinancialContext: false,
    routes: ['/', '/audit', '/analytics'],
  },
  MANAGER: {
    id: 'MANAGER',
    label: 'Sustainability Manager',
    description: 'Batch approvals, trend analysis, and oversight of the full ingestion pipeline.',
    icon: '📊',
    canUpload: true,
    canApprove: true,
    canBatchApprove: true,
    canExport: true,
    canViewRaw: false,
    showFinancialContext: true,
    routes: ['/', '/review', '/uploads', '/analytics', '/audit'],
  },
  CFO: {
    id: 'CFO',
    label: 'Chief Financial Officer',
    description: 'Executive summary view. Top-level KPIs, financial context, and board-ready metrics.',
    icon: '💼',
    canUpload: false,
    canApprove: false,
    canBatchApprove: false,
    canExport: true,
    canViewRaw: false,
    showFinancialContext: true,
    routes: ['/', '/analytics'],
  },
}

interface RoleContextValue {
  role: Role
  roleInfo: RoleInfo
  setRole: (r: Role) => void
  clearRole: () => void
  isAuthenticated: boolean
}

const RoleContext = createContext<RoleContextValue | null>(null)

const STORAGE_KEY = 'breathe_esg_role'

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<Role | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored && stored in ROLES ? (stored as Role) : null
  })

  const setRole = (r: Role) => {
    localStorage.setItem(STORAGE_KEY, r)
    setRoleState(r)
  }

  const clearRole = () => {
    localStorage.removeItem(STORAGE_KEY)
    setRoleState(null)
  }

  return (
    <RoleContext.Provider value={{
      role: role ?? 'ANALYST',
      roleInfo: ROLES[role ?? 'ANALYST'],
      setRole,
      clearRole,
      isAuthenticated: role !== null,
    }}>
      {children}
    </RoleContext.Provider>
  )
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used within RoleProvider')
  return ctx
}