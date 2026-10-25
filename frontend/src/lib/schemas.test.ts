/** VIXOR — Zod schema tests */

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
