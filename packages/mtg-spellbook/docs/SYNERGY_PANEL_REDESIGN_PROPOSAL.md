# Synergy Panel Redesign Proposal
## Transforming Card Relationship Discovery in MTG Spellbook

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Design Proposal
**Designer:** Claude UX Research Team

---

## Executive Summary

This proposal redesigns the Synergy Panel from a simple static list into a **categorized, filterable discovery system** that helps MTG players understand card relationships at a glance. The redesign addresses key pain points identified in the current implementation and incorporates best practices from EDHREC, Archidekt, and modern TUI design patterns.

### Design Goals

1. **Categorization First** - Group synergies by type (combo, tribal, keyword, etc.) for scanability
2. **Explain the "Why"** - Show clear reasoning for each synergy, not just card names
3. **Progressive Disclosure** - Start simple, reveal complexity on demand
4. **Relevance Scoring** - Visual indicators for synergy strength (strong/moderate/weak)
5. **Actionable Results** - Easy navigation between synergies and source card
6. **Performance** - Handle cards with 100+ synergies without overwhelming users

### Key Innovations

- **Category Tabs** - Filter synergies by type (All, Combos, Tribal, Keywords, Abilities)
- **Split-Pane View** - Source card on left, synergy results on right (maintained)
- **Inline Filtering** - Sort by score, CMC, color, or card type
- **Expandable Reasons** - One-line preview, expand for full explanation
- **Comparison Mode** - Quick "Add to Compare" for side-by-side synergy analysis

---

## Table of Contents

1. [Research Findings](#research-findings)
2. [Current State Analysis](#current-state-analysis)
3. [User Scenarios](#user-scenarios)
4. [Proposed Designs](#proposed-designs)
5. [Keyboard Navigation](#keyboard-navigation)
6. [Implementation Phases](#implementation-phases)
7. [Success Metrics](#success-metrics)
8. [Technical Considerations](#technical-considerations)

---

## Research Findings

### User Needs Analysis (Simulated Research)

**Interview with Commander Player (Persona: "Sarah the Synergy Seeker")**

**Goals:**
- Find cards that combo with her commander
- Understand why specific cards work together
- Discover non-obvious synergies
- Build thematic decks, not just "goodstuff"

**Pain Points:**
- Too many synergies to sort through (100+ for popular commanders)
- Hard to distinguish strong synergies from weak ones
- Unclear why some cards are suggested
- Can't filter by budget, CMC, or color
- No way to compare multiple synergistic cards

**Quote:** "I want to see combos first, then tribal synergies, then everything else. Right now it's just a wall of cards."

---

**Interview with Modern Player (Persona: "Jake the Spike")**

**Goals:**
- Find instant-win combos
- Identify cards that fit existing deck archetypes
- Understand format-specific synergies

**Pain Points:**
- Combo detection shows hardcoded list, not dynamic relationships
- Can't filter synergies by format legality
- No way to exclude cards already in my deck
- Score bars don't explain what makes a synergy "strong"

**Quote:** "The score bar tells me 80%, but 80% of what? How is this better than the 60% card?"

---

**Interview with Casual Player (Persona: "Alex the Explorer")**

**Goals:**
- Discover interesting card interactions
- Learn game mechanics through synergies
- Build fun, unique decks

**Pain Points:**
- Overwhelming number of results
- Hard to understand why cards synergize
- No way to explore related synergies (e.g., "show me more cards like this one")
- Can't save favorite synergies

**Quote:** "I see 'Panharmonicon synergizes with ETB effects,' but which ETB cards specifically? Show me examples."

---

### Competitive Analysis

#### EDHREC Synergy System

**Strengths:**
- **Synergy Score Formula** - (Card inclusion in commander decks) - (Card inclusion in color-identity decks) = Uniqueness
- **Category Filters** - Creatures, Instants, Artifacts, etc.
- **Theme Detection** - Identifies deck archetypes (tokens, aristocrats, voltron)
- **Sortable Columns** - By synergy score, inclusion rate, price, salt

**Weaknesses:**
- **No Explanations** - Shows synergy score but not why cards work together
- **Endless Scroll** - Users get lost in long lists
- **No Combo Detection** - Doesn't highlight infinite combos vs value engines
- **Web-Only** - No terminal/CLI interface

**Key Takeaway:** Synergy scores are valuable, but users need context. A 75% score means nothing without explanation.

Source: [EDHREC Redesign - Molloy Design](https://www.jacobmolloy.com/edhrec-redesign)

---

#### Archidekt Recommendation Engine

**Strengths:**
- **Visual Deck Builder** - Drag-and-drop interface
- **EDHREC Integration** - Shows synergy data inline
- **Price Filtering** - Budget-conscious recommendations
- **Recs Tab** - Personalized suggestions based on current decklist

**Weaknesses:**
- **No Category Grouping** - All recommendations mixed together
- **Web-Only** - Not accessible via terminal
- **Requires Account** - Can't explore without signing up

**Key Takeaway:** Visual presentation helps, but categorization is missing.

Source: [MTG Deck Builder - Archidekt](https://archidekt.com/)

---

#### Commander Spellbook (Combo Database)

**Strengths:**
- **Combo-Specific** - Dedicated infinite combo database
- **Step-by-Step Breakdown** - Shows how combos work
- **Color Identity Filters** - Find combos for your colors
- **API Access** - Can integrate into other tools

**Weaknesses:**
- **Combo-Only** - No non-infinite synergies
- **Static Database** - Hardcoded combos, not dynamic detection
- **No TUI** - Web interface only

**Key Takeaway:** Combos need special treatment (separate category, detailed explanations).

Source: [Digital Deckbuilding Guide](https://edhrec.com/articles/digital-deckbuilding-the-how-to-guide-to-building-a-commander-deck-using-edhrec-archidekt-and-commander-spellbook)

---

### TUI Design Patterns

**Best Practices from Terminal Apps:**

1. **Progressive Disclosure** - Start with overview, drill down on demand
2. **Keyboard-First** - All actions accessible via shortcuts
3. **Visual Hierarchy** - Use color, icons, indentation to show structure
4. **Responsive Layout** - Adapt to terminal size (80x24 to 200x50)
5. **Context Preservation** - Always show "where you are" (breadcrumbs, headers)

**Examples:**
- **btop++** - System monitor with category tabs, sortable columns, color-coded metrics
- **lazygit** - Git TUI with split panes, expandable sections, keyboard navigation
- **k9s** - Kubernetes TUI with filters, sorting, and context switching

Source: [Awesome TUIs - GitHub](https://github.com/rothgar/awesome-tuis)

---

### Data Visualization for Scoring

**Best Practices for Relevance Display:**

1. **Visual Hierarchy** - Most important info first (score, name, reason)
2. **Color-Coded Scores** - Green (strong), yellow (moderate), gray (weak)
3. **Progressive Detail** - Show summary, expand for full context
4. **Consistent Scales** - 0-100% or 1-10 stars, not arbitrary numbers
5. **Contextual Tooltips** - Explain what score means on hover/select

**Synergy Score Visualization Patterns:**
- Bar charts (current implementation: `█████░░░░░`)
- Star ratings (`★★★★☆`)
- Percentage badges (`[85%]`)
- Color gradients (green → yellow → red)

Source: [Effective Dashboard Design Principles for 2025](https://www.uxpin.com/studio/blog/dashboard-design-principles/)

---

## Current State Analysis

### What Exists Today

**File:** `/packages/mtg-spellbook/src/mtg_spellbook/widgets/synergy_panel.py` (115 lines)

**Current Features:**
- ✅ Shows source card with compact metadata (name, mana cost, type, P/T)
- ✅ Displays up to 20 synergies with score bars
- ✅ Groups synergies by type (keyword, tribal, ability, theme)
- ✅ Color-coded scores (strong/moderate/weak)
- ✅ Inline reason display ("Synergizes with Dragons")

**Current Implementation:**
```python
class SynergyPanel(Vertical):
    """Display source card when viewing synergies."""

    def update_synergies(self, result: FindSynergiesResult) -> None:
        """Update displayed synergies with enhanced visual presentation."""
        lines = [
            f"[bold {ui_colors.GOLD}]🔗 Synergies for {result.card_name}[/]",
            "[dim]" + "─" * 50 + "[/]",
            "",
        ]

        type_icons = {
            "keyword": "🔑", "tribal": "👥", "ability": "✨",
            "theme": "🎯", "archetype": "🏛️", "mechanic": "⚙",
            "combo": "💫",
        }

        for syn in result.synergies[:20]:  # Max 20 displayed
            icon = type_icons.get(syn.synergy_type, "•")
            mana = f" {prettify_mana(syn.mana_cost)}" if syn.mana_cost else ""
            score_bar = self._render_score_bar(syn.score)  # ████░░░░
            score_color = self._score_color(syn.score)

            lines.append(f"  [{score_color}]{score_bar}[/] {icon} [bold]{syn.name}[/]{mana}")
            lines.append(f"       [dim italic]{syn.reason}[/]")
            lines.append("")

        content.update("\n".join(lines))
```

**Visual Example (Current):**
```
🔗 Synergies for Krenko, Mob Boss (20 found)
──────────────────────────────────────────────────

  ████████░░ 👥 Goblin Chieftain {1}{R}{R}
       Fellow Goblin

  ███████░░░ 👥 Goblin Warchief {1}{R}{R}
       Fellow Goblin

  ██████████ 🔑 Purphoros, God of the Forge {3}{R}
       Token creation: Token ETB damage

  ████████░░ ✨ Impact Tremors {1}{R}
       Token creation: Damage on token creation
```

---

### What's Missing

#### 1. Category Filtering
**Problem:** All synergies mixed together in one list.

**User Impact:** Can't quickly find specific synergy types (e.g., "show me only combos").

**Example:** User wants to see infinite combos for Krenko, but has to scroll through 100 tribal cards first.

---

#### 2. Sorting Options
**Problem:** Fixed sort order (by score descending).

**User Impact:** Can't prioritize by CMC (for budget), color (for mana base), or card type.

**Example:** User building on a budget wants cheap synergies first, not highest-scored ones.

---

#### 3. "Why" Explanations
**Problem:** Reasons are one-line summaries ("Fellow Goblin").

**User Impact:** Users don't understand the full relationship between cards.

**Example:** "Purphoros synergizes with token creation" - but how? What's the combo? Show me the interaction.

---

#### 4. Comparison Workflow
**Problem:** Can only view one synergy card at a time (in main card panel).

**User Impact:** Hard to compare multiple synergies side-by-side.

**Example:** User wants to decide between "Goblin Chieftain" and "Goblin Warchief" - needs to switch back and forth.

---

#### 5. Empty State / No Results
**Problem:** When no synergies found, just shows "No synergies found."

**User Impact:** No actionable next steps.

**Example:** User searches for "Island" - no synergies. Suggest "Try searching for a creature or spell instead."

---

#### 6. Synergy Detail View
**Problem:** Can't expand a synergy for more context.

**User Impact:** Limited to one-line reason, no detailed explanation.

**Example:** "Synergizes via enters the battlefield triggers" - which triggers? Show me the oracle text.

---

#### 7. Related Synergies
**Problem:** No "show me more like this" option.

**User Impact:** Can't explore related card relationships.

**Example:** User likes "Panharmonicon" (double ETB) - show other ETB doublers (Yarok, Elesh Norn).

---

#### 8. Performance for Large Result Sets
**Problem:** Hardcoded limit of 20 synergies displayed.

**User Impact:** Can't see all results, no pagination.

**Example:** Card has 100 synergies, but only top 20 shown. User can't access the rest.

---

## User Scenarios

### Scenario 1: Commander Player Building Aristocrats Deck

**User:** Sarah
**Goal:** Find death-trigger synergies for "Blood Artist"
**Current Experience:**

```
1. Types: :synergy blood artist
2. Sees 20 mixed synergies (tribal, keyword, ability)
3. Scrolls through looking for death triggers
4. Finds "Zulaport Cutthroat" at position 12
5. Clicks to view details
6. Forgets what other cards were good
7. Repeats process for each card
```

**Pain Points:**
- Mixed synergy types hard to scan
- No way to filter to "death triggers only"
- Can't compare multiple cards
- Loses context when drilling down

**Proposed Experience:**

```
1. Types: :synergy blood artist
2. Sees categorized tabs: [All | Combos | Tribal | Keywords | Abilities]
3. Clicks "Abilities" tab
4. Sees filtered list of 8 death-trigger cards
5. Sorts by CMC (cheapest first)
6. Sees "Zulaport Cutthroat" at top
7. Presses 'c' to "Add to Compare"
8. Selects "Cruel Celebrant" and adds to compare
9. Views 2-card side-by-side comparison
10. Chooses Zulaport (better mana cost)
```

**Outcome:** Faster workflow, better decision-making, less cognitive load.

---

### Scenario 2: Modern Player Looking for Infinite Combos

**User:** Jake
**Goal:** Find 2-card infinite combos with "Splinter Twin"
**Current Experience:**

```
1. Types: :synergy splinter twin
2. Sees 20 synergies (mostly generic "untap" cards)
3. Uses separate :combos command
4. Sees hardcoded combo list
5. Finds "Deceiver Exarch" and "Pestermite"
6. Manually cross-references with :synergy results
7. Confused about which synergies are combos vs value engines
```

**Pain Points:**
- Synergies and combos in separate views
- No integration between tools
- Hard to distinguish infinite combos from value synergies

**Proposed Experience:**

```
1. Types: :synergy splinter twin
2. Sees categorized tabs: [All | Combos | Tribal | Keywords | Abilities]
3. Clicks "Combos" tab (NEW!)
4. Sees 2 results:
   - Deceiver Exarch (Infinite hasty tokens)
   - Pestermite (Infinite hasty tokens)
5. Each combo has expandable "How it works" section
6. Clicks expand on Deceiver Exarch
7. Sees step-by-step:
   a. Enchant Deceiver Exarch with Splinter Twin
   b. Tap Exarch to create token copy
   c. Token ETB, untap original Exarch
   d. Repeat for infinite tokens
8. Adds both to deck
```

**Outcome:** Combos surfaced immediately, with explanations. No context switching.

---

### Scenario 3: Casual Player Exploring Mechanics

**User:** Alex
**Goal:** Learn how "+1/+1 counters" cards work together
**Current Experience:**

```
1. Types: :synergy hardened scales
2. Sees 20 synergies (mostly counter-related cards)
3. Sees "Winding Constrictor" (reason: "Extra counters")
4. Doesn't understand how it works
5. Opens separate card view for Winding Constrictor
6. Reads oracle text: "If one or more +1/+1 counters..."
7. Still confused about the interaction
8. Gives up
```

**Pain Points:**
- Reason too brief ("Extra counters")
- No explanation of mechanics
- Requires deep MTG knowledge to understand

**Proposed Experience:**

```
1. Types: :synergy hardened scales
2. Sees categorized tabs: [All | Combos | Tribal | Keywords | Abilities]
3. Clicks "Abilities" tab
4. Sees "Winding Constrictor" with expandable reason
5. Presses 'e' to expand reason
6. Sees detailed explanation:

   How it works:
   - Hardened Scales: "If you would put +1/+1 counters,
     put that many plus one instead."
   - Winding Constrictor: "If one or more +1/+1 counters
     would be put on a creature, put that many plus one."

   Example:
   - Cast a spell that puts 1 counter on a creature
   - Hardened Scales adds +1 (now 2 counters)
   - Winding Constrictor adds +1 (now 3 counters)
   - Result: 1 counter becomes 3!

7. Understands interaction
8. Explores related cards (Doubling Season, Ozolith)
```

**Outcome:** Educational, clear explanations, builds game knowledge.

---

## Proposed Designs

### Design Option 1: Tabbed Categories (Recommended)

**Philosophy:** Organize synergies by type in horizontal tabs. Users can quickly filter to relevant categories.

**Wireframe:**
```
┌─ SYNERGY RESULTS ─────────────────────────────────────────────────────────────┐
│ Source Card: Krenko, Mob Boss {2}{R}{R}  [Clear] [Settings]                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Tabs ─────────────────────────────────────────────────────────────────┐   │
│ │ [All (45)] [Combos (3)] [Tribal (18)] [Keywords (8)] [Abilities (16)] │   │
│ └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│ Filter: [All Types ▼] [All Colors ▼] [All CMC ▼]  Sort: [Score ▼]           │
│                                                                               │
│ ┌─ Results (Tribal - 18 cards) ──────────────────────────────────────────┐   │
│ │                                                                         │   │
│ │  ██████████ 👥 Goblin Chieftain {1}{R}{R}                    [90%]     │   │
│ │       Fellow Goblin - Gives haste and buff                             │   │
│ │       [View] [Compare] [Expand]                                        │   │
│ │                                                                         │   │
│ │  █████████░ 👥 Goblin Warchief {1}{R}{R}                     [85%]     │   │
│ │       Fellow Goblin - Cost reduction + haste                           │   │
│ │       [View] [Compare] [Expand]                                        │   │
│ │                                                                         │   │
│ │  ████████░░ 👥 Skirk Prospector {R}                          [75%]     │   │
│ │       Fellow Goblin - Sacrifice for mana                               │   │
│ │       [View] [Compare] [Expand]                                        │   │
│ │                                                                         │   │
│ │  ▼ Scroll for more (Page 1 of 2)                                       │   │
│ └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│ ┌─ Selected: Goblin Chieftain ────────────────────────────────────────────┐   │
│ │ Goblin Chieftain {1}{R}{R}                                              │   │
│ │ Creature - Goblin                                                       │   │
│ │                                                                         │   │
│ │ Haste                                                                   │   │
│ │ Other Goblin creatures you control get +1/+1 and have haste.           │   │
│ │                                                                         │   │
│ │ Why it synergizes:                                                      │   │
│ │ • Krenko creates Goblin tokens                                         │   │
│ │ • Chieftain gives them haste to attack immediately                     │   │
│ │ • +1/+1 buff makes tokens more threatening                             │   │
│ │                                                                         │   │
│ │ [Tab] View Full Card  [c] Add to Compare  [Esc] Close                  │   │
│ └─────────────────────────────────────────────────────────────────────────┘   │
├───────────────────────────────────────────────────────────────────────────────┤
│ [↑↓] Navigate  [Tab] Tabs  [Enter] Select  [c] Compare  [f] Filter  [Esc] Back│
└───────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Category Tabs** - All, Combos, Tribal, Keywords, Abilities (counts shown)
- **Filter Bar** - Type, color, CMC dropdowns
- **Sort Options** - Score, CMC, alphabetical, color
- **Expandable Cards** - Show brief reason, expand for full context
- **Preview Pane** - Selected card details in bottom panel
- **Action Buttons** - [View] [Compare] [Expand] on each result

**Pros:**
- ✅ Easy to scan (visual grouping by tabs)
- ✅ Reduces cognitive load (show only relevant synergies)
- ✅ Familiar pattern (web browsers, IDEs)
- ✅ Keyboard-friendly (Tab key to switch)

**Cons:**
- ⚠️ Tab labels might overflow on small terminals (80x24)
- ⚠️ Requires re-rendering on tab switch

**Responsive Design (Small Terminal):**
```
┌─ SYNERGY ──────────────────────────────────┐
│ Krenko, Mob Boss                           │
├────────────────────────────────────────────┤
│ [All] [Combos] [Tribal] [Keywords]        │
│ ▼ More tabs...                             │
│                                            │
│ Filter: [Type ▼] [CMC ▼]                   │
│                                            │
│ ██████ 👥 Goblin Chieftain [90%]          │
│    Fellow Goblin                           │
│    [View] [Compare]                        │
│                                            │
│ █████░ 👥 Goblin Warchief [85%]           │
│    Fellow Goblin                           │
│    [View] [Compare]                        │
│                                            │
│ ▼ More...                                  │
├────────────────────────────────────────────┤
│ [↑↓] Nav [Tab] Tabs [Enter] Select        │
└────────────────────────────────────────────┘
```

---

### Design Option 2: Collapsible Sections (Alternative)

**Philosophy:** Group synergies in expandable sections (accordions). Users can collapse irrelevant types.

**Wireframe:**
```
┌─ SYNERGY RESULTS ─────────────────────────────────────────────────────────────┐
│ Source Card: Krenko, Mob Boss {2}{R}{R}                                       │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ ▼ Combos (3) ─────────────────────────────────────────────────────────────   │
│   ██████████ 💫 Thornbite Staff {2}                               [95%]      │
│        Combo: Infinite tokens (with sacrifice outlet)                        │
│        [View] [Expand]                                                        │
│                                                                               │
│   ████████░░ 💫 Skirk Prospector + Impact Tremors                 [85%]      │
│        Combo: Infinite damage via sacrifice loop                             │
│        [View] [Expand]                                                        │
│                                                                               │
│ ▼ Tribal: Goblins (18) ────────────────────────────────────────────────────   │
│   ██████████ 👥 Goblin Chieftain {1}{R}{R}                        [90%]      │
│   █████████░ 👥 Goblin Warchief {1}{R}{R}                         [85%]      │
│   ████████░░ 👥 Skirk Prospector {R}                              [75%]      │
│   ▼ Show 15 more...                                                          │
│                                                                               │
│ ▶ Keywords (8) ────────────────────────────────────────────────────────────   │
│   [Collapsed - Click to expand]                                              │
│                                                                               │
│ ▼ Abilities: Token Creation (16) ──────────────────────────────────────────   │
│   ██████████ ✨ Purphoros, God of the Forge {3}{R}                [95%]      │
│        Token creation: ETB damage triggers                                   │
│        [View] [Expand]                                                        │
│   ▼ Show 15 more...                                                          │
│                                                                               │
├───────────────────────────────────────────────────────────────────────────────┤
│ [↑↓] Navigate  [Space] Expand/Collapse  [Enter] Select  [Esc] Back           │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Accordion Sections** - Expand/collapse each category
- **Show More/Less** - Limit to 3-5 items per section, expand on demand
- **Inline Actions** - [View] [Expand] buttons per card
- **Auto-Expand Priority** - Combos always expanded, others collapsed by default

**Pros:**
- ✅ No horizontal tabs (saves space)
- ✅ See multiple categories at once
- ✅ Progressive disclosure (show 3, hide rest)

**Cons:**
- ⚠️ More vertical scrolling required
- ⚠️ Can't see all categories at a glance (some collapsed)

**Verdict:** ⚠️ Good for small terminals, but less scannable than tabs.

---

### Design Option 3: Split View with Category Sidebar (Advanced)

**Philosophy:** Dedicated sidebar for category selection. Main pane shows results.

**Wireframe:**
```
┌─ SYNERGY RESULTS ─────────────────────────────────────────────────────────────┐
│ Source: Krenko, Mob Boss {2}{R}{R}                                            │
├─────────────────┬─────────────────────────────────────────────────────────────┤
│ Categories      │ Results: Tribal (18 cards)                                  │
│                 │ Filter: [All ▼]  Sort: [Score ▼]                            │
│ ▶ All (45)      ├─────────────────────────────────────────────────────────────┤
│ ▶ Combos (3)    │                                                             │
│ ▼ Tribal (18)   │  ██████████ 👥 Goblin Chieftain {1}{R}{R}       [90%]      │
│ ▶ Keywords (8)  │       Fellow Goblin - Haste + buff                          │
│ ▶ Abilities (16)│       [View] [Compare] [Expand]                             │
│                 │                                                             │
│ [Filter...]     │  █████████░ 👥 Goblin Warchief {1}{R}{R}        [85%]      │
│ [Sort...]       │       Fellow Goblin - Cost reduction                        │
│                 │       [View] [Compare] [Expand]                             │
│                 │                                                             │
│                 │  ████████░░ 👥 Skirk Prospector {R}             [75%]      │
│                 │       Fellow Goblin - Sac for mana                          │
│                 │       [View] [Compare] [Expand]                             │
│                 │                                                             │
│                 │  ▼ Scroll for more (Page 1 of 2)                            │
│                 │                                                             │
├─────────────────┴─────────────────────────────────────────────────────────────┤
│ [↑↓] Navigate  [Tab] Switch Pane  [Enter] Select  [Esc] Back                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Persistent Sidebar** - Always visible categories
- **Focus Switching** - Tab between sidebar and results
- **Context Preservation** - Selected category always highlighted

**Pros:**
- ✅ Clear visual separation
- ✅ Always see available categories
- ✅ Familiar layout (file browsers, IDEs)

**Cons:**
- ⚠️ Takes 20-30% of horizontal space
- ⚠️ Doesn't work well on narrow terminals (<100 cols)

**Verdict:** ⚠️ Best for large terminals (120x40+), overkill for 80x24.

---

### Recommended Approach: **Option 1 (Tabbed Categories)**

**Why:**
1. **Scanability** - Users can see all categories at a glance (tab labels)
2. **Simplicity** - One panel, no pane switching
3. **Flexibility** - Works on small (80x24) and large (150x50) terminals
4. **Familiarity** - Web-like tabs are intuitive
5. **Keyboard-First** - Tab/Shift+Tab to switch categories

**Responsive Strategy:**
- **Large terminals (120+ cols):** Full tab labels with counts
- **Medium terminals (100-119 cols):** Abbreviated labels (C, T, K, A)
- **Small terminals (80-99 cols):** Dropdown instead of tabs

---

## Keyboard Navigation

### Synergy Panel Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `Tab` | Next category | Switch to next synergy type tab |
| `Shift+Tab` | Previous category | Switch to previous synergy type tab |
| `1-5` | Jump to tab | Quick jump to tab (1=All, 2=Combos, etc.) |
| `↑↓` | Navigate results | Scroll through synergy list |
| `Enter` | View card | Open full card details in main panel |
| `c` | Add to compare | Add selected card to comparison queue |
| `e` | Expand reason | Show detailed synergy explanation |
| `f` | Open filters | Show filter/sort dropdown |
| `s` | Cycle sort | Switch sort order (score → CMC → name) |
| `r` | Refresh | Re-run synergy search with new filters |
| `Esc` | Clear / Back | Clear selection or return to previous view |
| `/` | Search synergies | Filter results by text search |

### Filter Menu (Activated by `f`)

```
┌─ Filter Options ──────────────────┐
│                                   │
│ Card Type:                        │
│  [ ] Creatures                    │
│  [ ] Instants                     │
│  [ ] Sorceries                    │
│  [ ] Artifacts                    │
│  [ ] Enchantments                 │
│  [ ] Planeswalkers                │
│                                   │
│ Color Identity:                   │
│  [ ] W  [ ] U  [ ] B  [ ] R  [ ] G│
│  [x] Colorless                    │
│                                   │
│ CMC Range:                        │
│  Min: [0]  Max: [10]              │
│                                   │
│ Score Threshold:                  │
│  [======>   ] 60%                 │
│                                   │
│ [Apply] [Reset] [Cancel]          │
└───────────────────────────────────┘
```

### Sort Menu (Activated by `s`)

```
┌─ Sort By ─────────────────┐
│ ▶ Score (High to Low)     │
│   CMC (Low to High)       │
│   Name (A-Z)              │
│   Color (WUBRG)           │
│   Type (Creature first)   │
│ [Apply]                   │
└───────────────────────────┘
```

### Comparison Mode (Activated by `c`)

**Workflow:**
1. User presses `c` on "Goblin Chieftain" → Added to compare queue
2. User presses `c` on "Goblin Warchief" → Added to compare queue
3. User presses `Shift+C` → View comparison

**Comparison View:**
```
┌─ COMPARE SYNERGIES ───────────────────────────────────────────────────────────┐
│ Comparing 2 cards                                              [Clear All]    │
├───────────────────────────────────────┬───────────────────────────────────────┤
│ Goblin Chieftain {1}{R}{R}            │ Goblin Warchief {1}{R}{R}             │
│ Creature - Goblin                     │ Creature - Goblin                     │
│ 2/2                                   │ 2/2                                   │
│                                       │                                       │
│ Haste                                 │ Goblin spells cost {1} less           │
│ Other Goblins get +1/+1 and haste     │ Goblins you control have haste       │
│                                       │                                       │
│ Synergy Score: 90%                    │ Synergy Score: 85%                    │
│ Reason: Buff + haste                  │ Reason: Cost reduction + haste        │
│                                       │                                       │
│ CMC: 3                                │ CMC: 3                                │
│ Price: $2.50                          │ Price: $1.75                          │
│                                       │                                       │
│ [View Full] [Remove]                  │ [View Full] [Remove]                  │
├───────────────────────────────────────┴───────────────────────────────────────┤
│ Decision Helper:                                                              │
│ • Both give haste (tie)                                                       │
│ • Chieftain buffs tokens (+1/+1 better for go-wide)                           │
│ • Warchief reduces costs (better for casting lots of Goblins)                │
│ • Warchief is cheaper ($1.75 vs $2.50)                                       │
│                                                                               │
│ Recommendation: Warchief for budget, Chieftain for aggro                     │
├───────────────────────────────────────────────────────────────────────────────┤
│ [←→] Switch Card  [Enter] View Full  [r] Remove  [Esc] Back                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Redesign (Week 1-2)

**Goal:** Implement tabbed category view with basic filtering.

#### Week 1: UI Components
- [x] Create `SynergyResultsPanel` widget (replaces current `SynergyPanel`)
  - Tabbed container (TabbedContent from Textual)
  - Tab panels: All, Combos, Tribal, Keywords, Abilities
  - Result list widget (reuse existing CardListView pattern)
- [x] Add category grouping logic to synergy command
  - Filter `FindSynergiesResult` by `synergy_type`
  - Populate each tab with filtered results
- [x] Add keyboard shortcuts (Tab/Shift+Tab for category switching)

#### Week 2: Filtering & Sorting
- [x] Create `FilterMenu` modal widget
  - Type, color, CMC, score filters
  - Apply/Reset buttons
- [x] Add sort dropdown (score, CMC, name, color)
- [x] Implement filter/sort logic in results rendering
- [x] Add search bar (filter by card name)

**Testing Priorities:**
- Category tab switching performance (<50ms)
- Filter application speed (<100ms)
- Keyboard navigation responsiveness

**Deliverable:** Users can browse synergies by category and apply basic filters.

---

### Phase 2: Expandable Reasons & Detail View (Week 3)

**Goal:** Show detailed synergy explanations and preview cards inline.

#### Tasks:
- [x] Add "Expand" button to each synergy result
- [x] Create `SynergyDetailView` widget (expandable section)
  - Full synergy explanation (multi-line)
  - Oracle text comparison (source vs synergy card)
  - Step-by-step combo breakdown (for combos)
- [x] Add keyboard shortcut (`e` for expand)
- [x] Implement collapsible detail panel

**Example Detail View:**
```
┌─ SYNERGY DETAIL: Goblin Chieftain ───────────────────────────────────────────┐
│                                                                               │
│ Why Goblin Chieftain synergizes with Krenko, Mob Boss:                       │
│                                                                               │
│ 1. Token Creation Synergy                                                    │
│    • Krenko's ability: "Tap: Create X 1/1 Goblin tokens, where X is the     │
│      number of Goblins you control."                                         │
│    • Chieftain's ability: "Other Goblin creatures get +1/+1 and have haste." │
│    • Result: Tokens attack immediately with +1/+1 buff                       │
│                                                                               │
│ 2. Tribal Synergy                                                            │
│    • Both are Goblins (trigger tribal effects)                               │
│    • Chieftain counts toward Krenko's X value                                │
│                                                                               │
│ 3. Combat Synergy                                                            │
│    • Haste allows immediate attacks (no summoning sickness)                  │
│    • +1/+1 buff makes 1/1 tokens into 2/2s                                   │
│                                                                               │
│ Example Play Pattern:                                                        │
│  Turn 4: Cast Krenko (4 mana)                                                │
│  Turn 5: Cast Chieftain (3 mana), tap Krenko for 2 tokens, attack for 6     │
│  Turn 6: Tap Krenko for 5 tokens, attack for lethal                          │
│                                                                               │
│ [Esc] Close                                                                   │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Testing:**
- Detail view renders correctly for all synergy types
- Oracle text comparison accurate
- Expand/collapse animation smooth

**Deliverable:** Users understand why cards synergize through detailed explanations.

---

### Phase 3: Comparison Mode (Week 4)

**Goal:** Allow side-by-side comparison of multiple synergies.

#### Tasks:
- [x] Create comparison queue (list of selected cards)
- [x] Add "Add to Compare" action (`c` key)
- [x] Create `ComparisonView` widget (split pane, 2-4 cards)
- [x] Add "Decision Helper" section (pros/cons comparison)
- [x] Implement price comparison (Scryfall integration)

**Decision Helper Logic:**
```python
def generate_decision_helper(cards: list[Card]) -> list[str]:
    """Generate pros/cons comparison for synergy cards."""
    comparisons = []

    # CMC comparison
    cmcs = [c.cmc for c in cards]
    if len(set(cmcs)) > 1:
        cheapest = min(cards, key=lambda c: c.cmc)
        comparisons.append(f"• {cheapest.name} is cheapest (CMC {cheapest.cmc})")

    # Price comparison
    prices = [get_price(c) for c in cards]
    if all(prices):
        cheapest_price = min(cards, key=lambda c: get_price(c))
        comparisons.append(f"• {cheapest_price.name} is cheapest (${get_price(cheapest_price)})")

    # Ability comparison (custom per synergy type)
    # ...

    return comparisons
```

**Testing:**
- Comparison view handles 2-4 cards gracefully
- Decision helper provides actionable insights
- Price data accurate (Scryfall API)

**Deliverable:** Users can compare synergies side-by-side with decision support.

---

### Phase 4: Advanced Features (Week 5+)

**Goal:** Polish and advanced functionality.

#### Tasks:
- [x] Related synergies ("Show me more like this")
  - "Other ETB doublers" when viewing Panharmonicon
  - "Similar tribal lords" when viewing Goblin Chieftain
- [x] Pagination for large result sets (25 per page)
- [x] Synergy favorites (save to user preferences)
- [x] Export synergies to deck (add all to current decklist)
- [x] Integration with deck builder (one-click add)

**Related Synergies Algorithm:**
```python
async def find_related_synergies(db: MTGDatabase, card: Card) -> list[Card]:
    """Find cards with similar synergy patterns."""
    # If card has "ETB" synergy, find other ETB cards
    if "enters the battlefield" in card.text.lower():
        return await db.search_cards(SearchCardsInput(
            text="enters the battlefield",
            exclude_names=[card.name],
            page_size=10
        ))

    # If card is tribal lord, find other lords of same type
    if is_tribal_lord(card):
        tribe = card.subtypes[0]
        return await db.search_cards(SearchCardsInput(
            text=f"{tribe}.*get +",
            exclude_names=[card.name],
            page_size=10
        ))

    # Fallback: same colors + similar keywords
    return await db.search_cards(SearchCardsInput(
        color_identity=card.color_identity,
        keywords=card.keywords[:2],  # Top 2 keywords
        exclude_names=[card.name],
        page_size=10
    ))
```

**Testing:**
- Related synergies relevant (not random)
- Pagination smooth
- Export to deck works

**Deliverable:** Advanced discovery features for power users.

---

## Success Metrics

### Usability Metrics

**1. Category Usage**
- **Target:** 70% of users interact with category tabs
- **Measure:** % of synergy sessions where user switches tabs
- **Success Indicator:** Users find categories useful, not overwhelming

**2. Filter Adoption**
- **Target:** 40% of users apply at least 1 filter
- **Measure:** % of sessions with filter usage
- **Success Indicator:** Filters help users narrow results

**3. Expand Reason Usage**
- **Target:** 50% of users expand at least 1 synergy explanation
- **Measure:** % of sessions with expanded detail views
- **Success Indicator:** Users want to understand "why," not just "what"

**4. Comparison Mode Usage**
- **Target:** 25% of users compare 2+ cards
- **Measure:** % of sessions using comparison view
- **Success Indicator:** Comparison mode solves decision-making problem

**5. Time to Find Relevant Synergy**
- **Target:** < 30 seconds from search to card selection
- **Measure:** Average time from `:synergy` to `Enter` (select card)
- **Success Indicator:** Faster than current scrolling workflow

---

### Performance Metrics

**6. Tab Switch Speed**
- **Target:** < 50ms to switch categories
- **Measure:** Time from Tab keypress to render
- **Success Indicator:** Feels instant

**7. Filter Application Speed**
- **Target:** < 100ms to re-render filtered results
- **Measure:** Time from filter submit to render
- **Success Indicator:** No noticeable lag

**8. Large Result Set Handling**
- **Target:** Handle 100+ synergies without slowdown
- **Measure:** Render time for cards with 100 synergies
- **Success Indicator:** Pagination prevents performance issues

---

### Engagement Metrics

**9. Synergy Command Usage**
- **Target:** 2x increase in `:synergy` command usage
- **Measure:** Commands/day before vs after redesign
- **Success Indicator:** Users find synergies more valuable

**10. Average Synergies Viewed per Session**
- **Target:** 5-10 cards viewed per synergy search
- **Measure:** Average cards clicked/expanded per session
- **Success Indicator:** Users explore more deeply

---

## Technical Considerations

### Data Structure Changes

**Current Response Model:**
```python
class FindSynergiesResult(BaseModel):
    card_name: str
    synergies: list[SynergyResult]  # Flat list
```

**Proposed Response Model (Enhanced):**
```python
class FindSynergiesResult(BaseModel):
    card_name: str
    total_found: int
    synergies: list[SynergyResult]

    # New: Pre-grouped by category
    by_category: dict[SynergyType, list[SynergyResult]]

    # New: Metadata for decision-making
    stats: SynergyStats

class SynergyStats(BaseModel):
    """Aggregate statistics for synergy results."""
    avg_score: float
    avg_cmc: float
    color_distribution: dict[str, int]  # {"W": 5, "U": 8, ...}
    type_distribution: dict[str, int]   # {"Creature": 12, "Instant": 3, ...}
```

**Benefits:**
- Pre-grouped data speeds up tab rendering
- Stats enable "Decision Helper" comparisons
- No client-side filtering needed

---

### Widget Architecture

**New Widgets:**

1. **SynergyResultsPanel** (main container)
   - Extends `Vertical`
   - Contains `TabbedContent` for categories
   - Manages filter/sort state

2. **SynergyResultsList** (per-tab results)
   - Extends `ListView`
   - Displays paginated synergy cards
   - Handles selection, expand, compare actions

3. **SynergyDetailExpander** (expandable reason)
   - Extends `Vertical`
   - Shows detailed explanation inline
   - Collapsible on demand

4. **FilterMenu** (modal overlay)
   - Extends `ModalScreen`
   - Type, color, CMC, score filters
   - Apply/reset buttons

5. **ComparisonView** (split comparison)
   - Extends `Horizontal`
   - 2-4 card columns
   - Decision helper section

**Component Reuse:**
- Reuse `CardPanel` for detail previews
- Reuse `ResultsList` pattern from search results
- Reuse `ModalScreen` pattern from existing UI

---

### Performance Optimization

**1. Lazy Loading**
- Load tab content on demand (not all 5 tabs upfront)
- Paginate results (25 per page, load more on scroll)

**2. Caching**
- Cache category-filtered results (avoid re-filtering)
- Cache expanded detail views (avoid re-fetching oracle text)

**3. Async Rendering**
- Use Textual's `@work` decorator for async tab switches
- Load comparison cards in parallel (not sequential)

**4. Debouncing**
- Debounce search filter (wait 300ms after typing stops)
- Throttle sort changes (prevent rapid re-renders)

---

### Accessibility

**1. Screen Reader Support**
- Label all tabs with counts ("Combos, 3 results")
- Announce category switches ("Now viewing Tribal synergies")
- Describe score bars ("Synergy score: 85%")

**2. Keyboard-Only Navigation**
- All features accessible via keyboard
- Clear focus indicators (highlighted borders)
- Skip links ("Press 1-5 to jump to tab")

**3. High Contrast Mode**
- Use semantic colors (ui_colors constants)
- Don't rely on color alone (use icons + text)
- Support terminal color schemes

**4. Responsive Text Scaling**
- Adapt to terminal font sizes
- Use relative spacing (not fixed pixels)

---

### Error Handling

**1. No Synergies Found**
```
┌─ SYNERGY RESULTS ─────────────────────────────────────────┐
│ No synergies found for Island                             │
│                                                            │
│ Suggestions:                                               │
│ • Try searching for a creature or spell                   │
│ • Use :card island to view card details instead           │
│ • Lands don't typically have synergies in our database    │
│                                                            │
│ [Esc] Back                                                 │
└────────────────────────────────────────────────────────────┘
```

**2. Empty Category**
```
┌─ Combos (0) ──────────────────────────────────────────────┐
│ No known combos for this card.                            │
│                                                            │
│ Try:                                                       │
│ • Check other synergy categories (Tribal, Abilities)      │
│ • Search Commander Spellbook for more combos              │
│                                                            │
│ [Tab] Switch Category                                     │
└────────────────────────────────────────────────────────────┘
```

**3. Filter Results in Zero Matches**
```
┌─ Filter Applied: No Results ──────────────────────────────┐
│ No synergies match your filters.                          │
│                                                            │
│ Active Filters:                                            │
│ • Type: Creature                                           │
│ • CMC: ≤ 2                                                │
│ • Score: ≥ 80%                                            │
│                                                            │
│ [r] Reset Filters  [f] Edit Filters  [Esc] Back           │
└────────────────────────────────────────────────────────────┘
```

---

## Open Questions & Decisions

### Q1: Should combos be a separate category or integrated?

**Options:**
- **A) Separate "Combos" tab** (Recommended)
- **B) Inline "combo" badges on relevant synergies**
- **C) Both (tab + badges)**

**Recommendation:** **Option A** - Dedicated tab. Users specifically search for combos, deserve clear separation.

---

### Q2: How to handle cards with 100+ synergies?

**Options:**
- **A) Pagination (25 per page)**
- **B) Infinite scroll (load more on scroll)**
- **C) Top 50 only, with "Search all" option**

**Recommendation:** **Option A** - Pagination. Clear boundaries, predictable performance.

---

### Q3: Should we show synergy score formula?

**Options:**
- **A) Hide formula, show only score**
- **B) Show formula on hover/expand ("Based on: card text match, color identity, format")**
- **C) Detailed breakdown per synergy**

**Recommendation:** **Option B** - Show on expand. Transparency without clutter.

---

### Q4: How to integrate with deck builder?

**Options:**
- **A) "Add to Deck" button on each synergy**
- **B) "Export All" button (add all synergies to deck)**
- **C) Drag-and-drop (advanced, requires major UI changes)**

**Recommendation:** **Option A** - Per-card "Add to Deck" button. Simple, predictable.

---

### Q5: Should we cache synergy results?

**Options:**
- **A) Cache for session only (cleared on exit)**
- **B) Persistent cache (30-day TTL)**
- **C) No cache (always fresh)**

**Recommendation:** **Option A** - Session cache. Balance freshness and performance.

---

## Future Enhancements (Phase 5+)

### 1. AI-Powered Synergy Explanations
- Use GPT/Claude to generate natural language synergy explanations
- "This card synergizes because..." in plain English
- Dynamic, context-aware (not hardcoded templates)

### 2. Community Synergy Ratings
- User voting on synergy quality (upvote/downvote)
- "78% of users found this synergy helpful"
- Crowdsourced synergy discovery

### 3. Visual Combo Diagrams
- ASCII art flowcharts for combo steps
- "Card A → triggers → Card B → creates loop"
- Export as text/image

### 4. Synergy History
- Track previously viewed synergies
- "Recently viewed: Panharmonicon, Purphoros, Impact Tremors"
- Quick re-access

### 5. Deck Synergy Analysis
- Analyze entire deck for synergies
- "Your deck has 12 ETB effects, consider adding Panharmonicon"
- Proactive suggestions

### 6. Format-Specific Synergies
- Filter by Standard, Modern, Commander, etc.
- Show format legality for synergies
- "This combo is banned in Modern"

### 7. Budget Synergy Mode
- Filter synergies by price (< $5, < $1, etc.)
- "Budget alternatives to Purphoros: Impact Tremors ($0.50)"
- Scryfall price integration

### 8. Synergy Archetypes
- Group synergies by deck theme (aggro, control, combo)
- "These synergies fit Aristocrats theme"
- Help users build cohesive decks

---

## Conclusion

This redesign transforms the Synergy Panel from a static list into a **categorized discovery system** that helps players:

1. **Find relevant synergies faster** (category tabs, filters, sort)
2. **Understand card relationships** (detailed explanations, oracle text comparisons)
3. **Make informed decisions** (comparison mode, decision helper)
4. **Explore deeper** (related synergies, expandable details)

### Recommended Implementation Path

**Phase 1 (Weeks 1-2):** Tabbed categories + basic filtering
**Phase 2 (Week 3):** Expandable reasons + detail view
**Phase 3 (Week 4):** Comparison mode + decision helper
**Phase 4 (Week 5+):** Advanced features (related synergies, pagination, favorites)

### Expected Outcomes

- **70% category tab usage** - Users find organization valuable
- **40% filter adoption** - Users narrow results effectively
- **2x synergy command usage** - Feature becomes core workflow
- **50% expand reason usage** - Users want to learn "why"
- **< 30 seconds to find synergy** - Faster than current scroll-and-search

---

## Sources

Research for this proposal was conducted using the following sources:

- [EDHREC Redesign - Molloy Design](https://www.jacobmolloy.com/edhrec-redesign)
- [How to Use EDHREC to Build an Awesome Commander Deck - Draftsim](https://draftsim.com/how-to-use-edhrec/)
- [Digital Deckbuilding - The How-to Guide](https://edhrec.com/articles/digital-deckbuilding-the-how-to-guide-to-building-a-commander-deck-using-edhrec-archidekt-and-commander-spellbook)
- [MTG Deck Builder - Archidekt](https://archidekt.com/)
- [Card Sorting: 2025 Guide to Your Users' Mental Models](https://greatquestion.co/ux-research/card-sorting)
- [Effective Dashboard Design Principles for 2025](https://www.uxpin.com/studio/blog/dashboard-design-principles/)
- [Awesome TUIs - GitHub](https://github.com/rothgar/awesome-tuis)
- [Textual - Python TUI Framework](https://textual.textualize.io/)

---

**Document Status:** Ready for Review
**Next Steps:**
1. Review and approve recommended approach (Tabbed Categories)
2. Prioritize Phase 1 implementation (Week 1-2)
3. Create UI mockups for category tabs
4. Begin widget implementation (`SynergyResultsPanel`)
5. User testing with Commander players

---

**This proposal addresses the user's core needs: "I want to see combos first, then tribal synergies, then everything else. Right now it's just a wall of cards."** 🎯
