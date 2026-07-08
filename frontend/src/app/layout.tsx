/**
 * app/layout.tsx
 * ==============
 * Next.js 14 App Router — Root layout.
 *
 * Provides the application shell that wraps every page in the /app directory.
 * Registers global providers:
 *  • <QueryProvider>  — TanStack Query v5 client (React Query cache + devtools)
 *
 * Font: Inter (Google Fonts via next/font) — matches the CSS system font stack
 * already used in page.module.css and the form CSS module.
 */

import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { QueryProvider } from '@/providers/QueryProvider'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    default: 'AI-Native ERP',
    template: '%s | AI-Native ERP',
  },
  description:
    'Multi-tenant AI-Native ERP — Manufacturing, Retail, and Services inventory management powered by FastAPI and Supabase.',
  robots: { index: false, follow: false },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  )
}
