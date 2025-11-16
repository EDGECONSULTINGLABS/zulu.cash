import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'ZULU - Private AI Agent for Zcash',
  description: 'Privacy-first AI wallet intelligence with Zcash shielded transactions',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-dark-bg text-gray-100">{children}</body>
    </html>
  )
}
