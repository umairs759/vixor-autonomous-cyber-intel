/** VIXOR — Zod schemas mirroring backend Pydantic models.

All form inputs and API response shapes are validated here.
 */

import { z } from "zod"

// Shared
export const UUIDSchema = z.string().uuid("Invalid UUID")

// Auth
export const LoginSchema = z.object({
  email: z.string().email("Invalid email address").min(1, "Email is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
})

export type LoginInput = z.infer<typeof LoginSchema>

export const AuthTokensSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
})

export type AuthTokens = z.infer<typeof AuthTokensSchema>

// User
export const UserRoleSchema = z.enum(["admin", "analyst", "viewer"])

export const UserSchema = z.object({
  id: UUIDSchema,
  email: z.string().email(),
  role: UserRoleSchema,
  is_active: z.boolean(),
  created_at: z.string().datetime(),
})

export type User = z.infer<typeof UserSchema>

export const CreateUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  role: UserRoleSchema,
})

export type CreateUserInput = z.infer<typeof CreateUserSchema>

// Project
export const ProjectSchema = z.object({
  id: UUIDSchema,
  owner_id: UUIDSchema,
  name: z.string().min(1).max(200),
  description: z.string().optional(),
  created_at: z.string().datetime(),
})

export type Project = z.infer<typeof ProjectSchema>

export const CreateProjectSchema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().optional(),
})

export type CreateProjectInput = z.infer<typeof CreateProjectSchema>

// Domain
export const DomainStatusSchema = z.enum(["unverified", "verified", "suspended"])

export const DomainSchema = z.object({
  id: UUIDSchema,
  project_id: UUIDSchema,
  root_domain: z.string().min(1),
  verification_token: z.string(),
  verification_method: z.enum(["dns_txt", "file"]),
  status: DomainStatusSchema,
  verified_at: z.string().datetime().nullable(),
  last_reverified_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
})

export type Domain = z.infer<typeof DomainSchema>

export const RegisterDomainSchema = z.object({
  root_domain: z
    .string()
    .min(1)
    .max(253)
    .regex(
      /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/,
      "Invalid domain name"
    ),
  verification_method: z.enum(["dns_txt", "file"]),
})

export type RegisterDomainInput = z.infer<typeof RegisterDomainSchema>

// Scan
export const ScanStatusSchema = z.enum([
  "queued",
  "running",
  "partial",
  "completed",
  "failed",
])

export const ScanSchema = z.object({
  id: UUIDSchema,
  project_id: UUIDSchema,
  domain_id: UUIDSchema,
  triggered_by: UUIDSchema,
  status: ScanStatusSchema,
  started_at: z.string().datetime().nullable(),
  finished_at: z.string().datetime().nullable(),
  error_summary: z.string().nullable(),
  created_at: z.string().datetime(),
})

export type Scan = z.infer<typeof ScanSchema>

export const CreateScanSchema = z.object({
  domain_id: UUIDSchema,
  asset_ids: z.array(UUIDSchema).min(1, "Select at least one asset"),
})

export type CreateScanInput = z.infer<typeof CreateScanSchema>

// Finding
export const FindingSchema = z.object({
  id: UUIDSchema,
  asset_id: UUIDSchema,
  scan_id: UUIDSchema,
  fingerprint: z.string(),
  source_tool: z.enum(["nmap", "zap", "nuclei"]),
  title: z.string(),
  description: z.string(),
  severity_raw: z.string(),
  cvss: z.number().nullable(),
  cve_ids: z.array(z.string()),
  evidence: z.record(z.unknown()),
  remediation: z.string().nullable(),
  created_at: z.string().datetime(),
})

export type Finding = z.infer<typeof FindingSchema>

// Finding score
export const FindingScoreSchema = z.object({
  finding_id: UUIDSchema,
  risk_score: z.number().min(0).max(100),
  risk_class: z.enum(["low", "medium", "high", "critical"]),
  model_version: z.string(),
  features: z.record(z.unknown()),
  shap_values: z.record(z.number()),
  narrative: z.string(),
  scored_by: z.enum(["ml", "fallback"]),
})

export type FindingScore = z.infer<typeof FindingScoreSchema>

// Schedule
export const ScheduleSchema = z.object({
  id: UUIDSchema,
  domain_id: UUIDSchema,
  cron: z.enum(["daily", "weekly"]),
  is_active: z.boolean(),
  last_run_at: z.string().datetime().nullable(),
})

export type Schedule = z.infer<typeof ScheduleSchema>

// API error
export const ApiErrorSchema = z.object({
  detail: z.string().optional(),
  status: z.number().optional(),
})

export type ApiError = z.infer<typeof ApiErrorSchema>
