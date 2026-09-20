export function passphraseStrength(passphrase) {
  const value = typeof passphrase === "string" ? passphrase : ""
  const checks = {
    length: value.length >= 8,
    mixedCase: /[a-z]/.test(value) && /[A-Z]/.test(value),
    number: /\d/.test(value),
    symbol: /[^A-Za-z0-9]/.test(value),
  }
  const score = Object.values(checks).filter(Boolean).length
  let label = "Too short"
  if (value.length >= 8 && score <= 1) label = "Weak"
  else if (score === 2) label = "Fair"
  else if (score === 3) label = "Strong"
  else if (score === 4) label = "Very strong"
  return { checks, score, label }
}
