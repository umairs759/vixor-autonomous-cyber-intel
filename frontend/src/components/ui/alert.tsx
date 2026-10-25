"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const alertVariants = cva(
  "relative w-full rounded-lg border p-4 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-current [&>svg]:w-4 [&>svg]:h-4",
  {
    variants: {
      variant: {
        default: "bg-background text-text",
        destructive:
          "border-destructive/50 text-destructive dark:border-destructive/50 dark:text-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

interface AlertProps
  extends React.Attributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string
  description?: string
}

function Alert({ className, variant, title, description }: AlertProps) {
  return (
    <div className={cn(alertVariants({ variant }), className)} role="alert">
      {title && <h2 className="mb-1 font-medium">{title}</h2>}
      {description && (
        <p className="text-sm">{description}</p>
      )}
    </div>
  )
}

interface AlertTitleProps extends React.Attributes<HTMLHeadingElement> {
  children: React.ReactNode
}

function AlertTitle({ className, ...props }: AlertTitleProps) {
  return (
    <h3
      className={cn("mb-1 font-medium leading-none tracking-tight", className)}
      {...props}
    />
  )
}

interface AlertDescriptionProps extends React.Attributes<HTMLParagraphElement> {
  children: React.ReactNode
}

function AlertDescription({ className, ...props }: AlertDescriptionProps) {
  return (
    <p
      className={cn("text-sm [&_p]:leading-relaxed", className)}
      {...props}
    />
  )
}

export { Alert, AlertTitle, AlertDescription }
