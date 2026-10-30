"use client"

import React from "react"

type TableHeaderProps = {
  children: React.ReactNode
  className?: string
}

type TableRowProps = {
  children: React.ReactNode
  className?: string
}

type TableCellProps = {
  children: React.ReactNode
  className?: string
}

/* Exported components matching the imports used in pages */
export const Table = ({ className, children }: { className?: string; children: React.ReactNode }) => (
  <table className={`w-full caption-bottom text-sm ${className}`}>
    <tbody>{children}</tbody>
  </table>
)

export const TableHeader = ({ className, children }: TableHeaderProps) => (
  <tr className={`text-left text-muted text-xs font-mono ${className}`}>
    {children}
  </tr>
)

export const TableRow = ({ className, children }: TableRowProps) => (
  <tr className={`border-b border-border/50 hover:bg-elevated/50 ${className}`}>
    {children}
  </tr>
)

export const TableCell = ({ className, children }: TableCellProps) => (
  <td className={`py-2 whitespace-nowrap ${className}`}>
    {children}
  </td>
)

export const TableBody = ({ className, children }: { className?: string; children: React.ReactNode }) => (
  <tbody className={className}>{children}</tbody>
)