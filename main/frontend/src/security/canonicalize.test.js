import { describe, expect, it } from "vitest"
import { canonicalize } from "./canonicalize.js"

describe("canonicalize", () => {
  it("sorts nested object keys", () => {
    const a = canonicalize({ b: 1, a: { z: 2, m: 3 } })
    const b = canonicalize({ a: { m: 3, z: 2 }, b: 1 })
    expect(a).toBe(b)
    expect(a).toBe('{"a":{"m":3,"z":2},"b":1}')
  })

  it("preserves array order", () => {
    expect(canonicalize({ items: [2, 1] })).toBe('{"items":[2,1]}')
  })
})
