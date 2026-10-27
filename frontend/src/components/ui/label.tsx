"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

type LabelProps = React.LabelHTMLAttributes<HTMLLabelElement>

function Label({ className, ...props }: LabelProps) {
  return (
    <label
      className={cn(
        "px-2 py-1.5 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        className
      )}
      {...props}
    />
  )
}

export { Label }
