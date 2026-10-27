/** VIXOR — Zod schema tests */

// Jest globals are available at runtime via the jest test runner.
declare const describe: (name: string, fn: () => void) => void
declare const it: (name: string, fn: () => void) => void
declare const expect: {
  <T>(actual: T): {
    toBe: (expected: unknown) => void
    toBeTruthy: () => void
    toBeFalsy: () => void
    not: { toBe: (expected: unknown) => void }
  }
}

import { LoginSchema, RegisterDomainSchema } from "./schemas"

describe("LoginSchema", () => {
  it("accepts valid credentials", () => {
    const result = LoginSchema.safeParse({
      email: "admin@example.com",
      password: "SecurePass123!",
    })
    expect(result.success).toBe(true)
  })

  it("rejects missing email", () => {
    const result = LoginSchema.safeParse({
      email: "",
      password: "SecurePass123!",
    })
    expect(result.success).toBe(false)
  })

  it("rejects short password", () => {
    const result = LoginSchema.safeParse({
      email: "admin@example.com",
      password: "short",
    })
    expect(result.success).toBe(false)
  })
})

describe("RegisterDomainSchema", () => {
  it("accepts valid domain", () => {
    const result = RegisterDomainSchema.safeParse({
      root_domain: "example.com",
      verification_method: "dns_txt",
    })
    expect(result.success).toBe(true)
  })

  it("rejects invalid domain", () => {
    const result = RegisterDomainSchema.safeParse({
      root_domain: "not a domain",
      verification_method: "dns_txt",
    })
    expect(result.success).toBe(false)
  })

  it("rejects IP address as domain", () => {
    const result = RegisterDomainSchema.safeParse({
      root_domain: "192.168.1.1",
      verification_method: "dns_txt",
    })
    expect(result.success).toBe(false)
  })
})
