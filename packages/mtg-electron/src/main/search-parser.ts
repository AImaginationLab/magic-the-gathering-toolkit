/**
 * Search query parser - parses filter syntax into search parameters.
 *
 * Supports filters:
 *   t:creature - card type
 *   c:RG - colors
 *   ci:WU - color identity
 *   cmc:3 - mana value (exact)
 *   cmc>2 cmc<5 - mana value range
 *   f:modern - format legality
 *   r:mythic - rarity
 *   set:MH2 - set code
 *   text:"draw a card" - oracle text
 *   kw:flying - keyword
 *   artist:"Name" - artist name
 *   pow:4 - power
 *   tou:5 - toughness
 */

export interface SearchFilters {
  name?: string
  type?: string
  colors?: string[]
  color_identity?: string[]
  cmc?: number
  cmc_min?: number
  cmc_max?: number
  format_legal?: string
  rarity?: string
  set_code?: string
  text?: string
  keywords?: string[]
  artist?: string
  power?: string
  toughness?: string
  page_size?: number
}

/**
 * Parse a search query string into structured filters.
 */
export function parseSearchQuery(query: string): SearchFilters {
  const filters: SearchFilters = { page_size: 50 }
  const nameParts: string[] = []

  // Tokenize handling quoted strings
  const tokens = tokenize(query)

  for (const token of tokens) {
    // Check for comparison operators (cmc>3, cmc<5, cmc>=2)
    const compMatch = token.match(/^(cmc|pow|tou)(>=?|<=?|=)(\d+)$/i)
    if (compMatch) {
      const [, field, op, value] = compMatch
      const numValue = parseInt(value, 10)

      if (field.toLowerCase() === 'cmc') {
        if (op === '=' || op === ':') {
          filters.cmc = numValue
        } else if (op === '>' || op === '>=') {
          filters.cmc_min = op === '>=' ? numValue : numValue + 1
        } else if (op === '<' || op === '<=') {
          filters.cmc_max = op === '<=' ? numValue : numValue - 1
        }
      } else if (field.toLowerCase() === 'pow') {
        filters.power = value
      } else if (field.toLowerCase() === 'tou') {
        filters.toughness = value
      }
      continue
    }

    // Check for key:value pairs
    if (token.includes(':')) {
      const colonIdx = token.indexOf(':')
      const key = token.slice(0, colonIdx).toLowerCase()
      const value = token.slice(colonIdx + 1)

      if (!value) {
        nameParts.push(token)
        continue
      }

      switch (key) {
        case 't':
        case 'type':
          filters.type = value
          break
        case 'c':
        case 'color':
          filters.colors = value.toUpperCase().split('')
          break
        case 'ci':
        case 'id':
          filters.color_identity = value.toUpperCase().split('')
          break
        case 'cmc':
        case 'mv':
          if (/^\d+$/.test(value)) {
            filters.cmc = parseInt(value, 10)
          }
          break
        case 'f':
        case 'format':
          filters.format_legal = value.toLowerCase()
          break
        case 'r':
        case 'rarity':
          filters.rarity = normalizeRarity(value)
          break
        case 'set':
        case 's':
        case 'e':
          filters.set_code = value.toUpperCase()
          break
        case 'text':
        case 'o':
          filters.text = value
          break
        case 'kw':
        case 'keyword':
          filters.keywords = [value]
          break
        case 'artist':
        case 'a':
          filters.artist = value
          break
        case 'pow':
        case 'power':
          filters.power = value
          break
        case 'tou':
        case 'toughness':
          filters.toughness = value
          break
        default:
          // Unknown filter, treat as part of name
          nameParts.push(token)
      }
    } else {
      nameParts.push(token)
    }
  }

  if (nameParts.length > 0) {
    filters.name = nameParts.join(' ')
  }

  return filters
}

/**
 * Tokenize a query string, respecting quoted strings.
 */
function tokenize(query: string): string[] {
  const tokens: string[] = []
  let current = ''
  let inQuotes = false
  let quoteChar = ''

  for (let i = 0; i < query.length; i++) {
    const char = query[i]

    if (!inQuotes && (char === '"' || char === "'")) {
      inQuotes = true
      quoteChar = char
      // Don't include the quote in the token
    } else if (inQuotes && char === quoteChar) {
      inQuotes = false
      quoteChar = ''
      // Don't include the quote in the token
    } else if (!inQuotes && /\s/.test(char)) {
      if (current) {
        tokens.push(current)
        current = ''
      }
    } else {
      current += char
    }
  }

  if (current) {
    tokens.push(current)
  }

  return tokens
}

/**
 * Normalize rarity aliases.
 */
function normalizeRarity(value: string): string {
  const lower = value.toLowerCase()
  const aliases: Record<string, string> = {
    c: 'common',
    u: 'uncommon',
    r: 'rare',
    m: 'mythic',
    mythicrare: 'mythic',
    // Full names pass through
    common: 'common',
    uncommon: 'uncommon',
    rare: 'rare',
    mythic: 'mythic',
  }
  return aliases[lower] || lower
}

/**
 * Check if query contains filter syntax.
 */
export function hasQueryFilters(query: string): boolean {
  return /\b(t|c|ci|cmc|mv|f|r|set|s|e|text|o|kw|artist|a|pow|tou):/i.test(query)
}
