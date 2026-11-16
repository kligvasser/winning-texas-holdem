/**
 * Read a typed numeric answer leniently: "25", "25%", " 25 % ", "0,25" (decimal comma) and
 * fractions such as "1/3" (taken as a percentage when the question asks for %).
 * Returns null when the text is not a number.
 */
export function parseAnswer(text: string, unit = ''): number | null {
  const clean = text.trim().replace(/%$/, '').trim().replace(',', '.')
  if (clean === '') return null
  const fraction = /^(-?\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)$/.exec(clean)
  if (fraction) {
    const value = Number(fraction[1]) / Number(fraction[2])
    if (!Number.isFinite(value)) return null
    const scaled = unit === '%' ? value * 100 : value
    return Math.round(scaled * 100) / 100
  }
  const value = Number(clean)
  return Number.isFinite(value) ? value : null
}
