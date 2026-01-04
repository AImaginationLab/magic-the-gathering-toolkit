/**
 * Parse a search query string into SearchCardsInput filters.
 *
 * Supports filters like:
 * - t:creature (type)
 * - c:UB (colors)
 * - cmc:3 (mana value)
 * - r:mythic (rarity)
 * - set:MH3 (set code)
 * - f:modern (format)
 * - text:"draw a card" (oracle text)
 * - kw:flying (keyword)
 * - artist:"Name" (artist)
 *
 * Remaining text after filters is treated as the card name.
 */

import type {
  SearchCardsInput,
  Color,
  Rarity,
  Format,
} from "../../../shared/types/api";

const RARITY_MAP: Record<string, Rarity> = {
  common: "common",
  c: "common",
  uncommon: "uncommon",
  u: "uncommon",
  rare: "rare",
  r: "rare",
  mythic: "mythic",
  m: "mythic",
};

const COLOR_MAP: Record<string, Color> = {
  w: "W",
  white: "W",
  u: "U",
  blue: "U",
  b: "B",
  black: "B",
  r: "R",
  red: "R",
  g: "G",
  green: "G",
};

const FORMAT_MAP: Record<string, Format> = {
  standard: "standard",
  modern: "modern",
  legacy: "legacy",
  vintage: "vintage",
  commander: "commander",
  edh: "commander",
  pioneer: "pioneer",
  pauper: "pauper",
  historic: "historic",
  brawl: "brawl",
  alchemy: "alchemy",
  explorer: "explorer",
  timeless: "timeless",
};

function parseColors(colorString: string): Color[] {
  const colors: Color[] = [];
  const normalized = colorString.toLowerCase();

  for (const char of normalized) {
    const color = COLOR_MAP[char];
    if (color && !colors.includes(color)) {
      colors.push(color);
    }
  }

  return colors;
}

function extractQuotedValue(value: string): string {
  if (value.startsWith('"') && value.endsWith('"')) {
    return value.slice(1, -1);
  }
  if (value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1);
  }
  return value;
}

export function parseSearchQuery(query: string): SearchCardsInput {
  const filters: SearchCardsInput = {
    page: 1,
    page_size: 50,
  };

  // Prevent potential DoS with excessively long queries
  if (query.length > 1000) {
    return { ...filters, name: query.slice(0, 200) };
  }

  // Match quoted strings and key:value pairs
  const tokenRegex =
    /(\w+):"([^"]+)"|(\w+):'([^']+)'|(\w+):(\S+)|"([^"]+)"|'([^']+)'|(\S+)/g;

  const nameTokens: string[] = [];
  let match: RegExpExecArray | null;

  while ((match = tokenRegex.exec(query)) !== null) {
    // Handle key:"quoted value" or key:'quoted value'
    if (match[1] && match[2]) {
      processFilter(match[1].toLowerCase(), match[2], filters);
    } else if (match[3] && match[4]) {
      processFilter(match[3].toLowerCase(), match[4], filters);
    }
    // Handle key:value
    else if (match[5] && match[6]) {
      processFilter(match[5].toLowerCase(), match[6], filters);
    }
    // Handle quoted name parts
    else if (match[7]) {
      nameTokens.push(match[7]);
    } else if (match[8]) {
      nameTokens.push(match[8]);
    }
    // Handle unquoted name parts
    else if (match[9]) {
      nameTokens.push(match[9]);
    }
  }

  // Combine remaining tokens as the name filter
  if (nameTokens.length > 0) {
    filters.name = nameTokens.join(" ");
  }

  return filters;
}

function processFilter(
  key: string,
  value: string,
  filters: SearchCardsInput,
): void {
  const cleanValue = extractQuotedValue(value);

  switch (key) {
    case "t":
    case "type":
      filters.type = cleanValue;
      break;

    case "c":
    case "color":
    case "colors":
      filters.colors = parseColors(cleanValue);
      break;

    case "ci":
    case "identity":
    case "coloridentity":
      filters.color_identity = parseColors(cleanValue);
      break;

    case "cmc":
    case "mv":
    case "manavalue":
      const cmcNum = parseInt(cleanValue, 10);
      if (!isNaN(cmcNum)) {
        filters.cmc = cmcNum;
      }
      break;

    case "cmc<":
    case "mv<":
      const maxCmc = parseInt(cleanValue, 10);
      if (!isNaN(maxCmc)) {
        filters.cmc_max = maxCmc - 1;
      }
      break;

    case "cmc<=":
    case "mv<=":
      const maxCmcEq = parseInt(cleanValue, 10);
      if (!isNaN(maxCmcEq)) {
        filters.cmc_max = maxCmcEq;
      }
      break;

    case "cmc>":
    case "mv>":
      const minCmc = parseInt(cleanValue, 10);
      if (!isNaN(minCmc)) {
        filters.cmc_min = minCmc + 1;
      }
      break;

    case "cmc>=":
    case "mv>=":
      const minCmcEq = parseInt(cleanValue, 10);
      if (!isNaN(minCmcEq)) {
        filters.cmc_min = minCmcEq;
      }
      break;

    case "r":
    case "rarity":
      const rarity = RARITY_MAP[cleanValue.toLowerCase()];
      if (rarity) {
        filters.rarity = rarity;
      }
      break;

    case "set":
    case "s":
    case "e":
    case "edition":
      filters.set_code = cleanValue.toUpperCase();
      break;

    case "f":
    case "format":
    case "legal":
      const format = FORMAT_MAP[cleanValue.toLowerCase()];
      if (format) {
        filters.format_legal = format;
      }
      break;

    case "text":
    case "o":
    case "oracle":
      filters.text = cleanValue;
      break;

    case "kw":
    case "keyword":
    case "keywords":
      filters.keywords = [cleanValue];
      break;

    case "artist":
    case "a":
      filters.artist = cleanValue;
      break;

    case "pow":
    case "power":
      filters.power = cleanValue;
      break;

    case "tou":
    case "toughness":
      filters.toughness = cleanValue;
      break;

    case "subtype":
    case "sub":
      filters.subtype = cleanValue;
      break;

    case "supertype":
    case "super":
      filters.supertype = cleanValue;
      break;

    default:
      // Unknown filter, ignore
      break;
  }
}
