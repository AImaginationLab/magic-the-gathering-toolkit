"""CSS styles for the MTG Spellbook TUI."""

APP_CSS = """
/* ═══════════════════════════════════════════════════════════
   MTG SPELLBOOK - Card Frame Inspired Design
   ═══════════════════════════════════════════════════════════ */

Screen {
    background: #0d0d0d;
    layout: grid;
    grid-size: 1;
    grid-rows: auto 1fr auto auto;
}

/* ─── Header: Epic Banner ─── */
#header-content {
    width: 100%;
    height: 5;
    background: #0a0a14;
    border-bottom: heavy #c9a227;
    padding: 1 2;
    content-align: center middle;
    text-align: center;
    color: #c9a227;
}

/* ─── Main Layout ─── */
#main-container {
    width: 100%;
    height: 100%;
}

/* ─── Results: Card Stack ─── */
#results-container {
    width: 35;
    height: 100%;
    background: #121212;
    border-right: solid #3d3d3d;
}

#results-header {
    height: 3;
    background: #1a1a1a;
    border-bottom: solid #3d3d3d;
    padding: 0 1;
    content-align: center middle;
    color: #888;
}

#results-list {
    height: 100%;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
    scrollbar-color-active: #fff8dc;
}

#results-list > ListItem {
    padding: 0 1;
    height: auto;
    border-bottom: solid #1a1a1a;
}

#results-list > ListItem:hover {
    background: #1a1a2e;
}

#results-list > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

/* ─── Card Panel: Main Display ─── */
#detail-container {
    height: 100%;
    background: #0d0d0d;
}

/* Container for side-by-side card comparison in synergy mode */
#card-comparison-container {
    width: 100%;
    height: 100%;
}

#card-panel {
    width: 100%;
    height: 100%;
    background: #151515;
    border: round #2a2a2a;
    margin: 0 1;
}

/* When in synergy mode, card panel takes right half */
#card-panel.synergy-mode {
    width: 50%;
    height: 100%;
}

/* ─── Source Card Panel (Synergy Mode Right Side) ─── */
#source-card-panel {
    width: 0;
    height: 100%;
    display: none;
    background: #151515;
    border: round #2a2a2a;
    border-left: solid #c9a227;
    margin: 0 1 0 0;
}

#source-card-panel.visible {
    width: 50%;
    display: block;
}

#source-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: solid #c9a227;
    padding: 0 1;
    content-align: center middle;
    color: #c9a227;
}

#source-scroll {
    height: 1fr;
    padding: 1 2;
    background: #151515;
    scrollbar-color: #c9a227;
}

#source-card-text {
    background: #151515;
}

/* ─── Tabs: Tome Navigation ─── */
#card-tabs {
    height: 100%;
}

Tabs {
    background: #1a1a1a;
    border-bottom: solid #3d3d3d;
}

Tab {
    background: #1a1a1a;
    color: #777;
    padding: 0 2;
}

Tab:hover {
    background: #252525;
    color: #bbb;
}

Tab.-active {
    background: #252530;
    color: #e6c84a;
    text-style: bold;
}

Tab:focus {
    text-style: bold;
}

Underline > .underline--bar {
    color: #c9a227;
    background: #c9a227;
}

TabPane {
    padding: 1 2;
    background: #151515;
}

/* Fix focused/highlighted text contrast */
*:focus {
    text-style: none;
}

TabPane:focus-within {
    background: #151515;
}

/* ─── Card Text Area ─── */
/* Match any card-text widget (prefixed IDs like card-panel-card-text) */
Static.-card-text {
    background: #151515;
}

/* ─── Art Gallery ─── */
/* Match any tab-art (prefixed IDs like card-panel-tab-art) */
TabPane.-tab-art {
    layout: vertical;
    align: center middle;
    background: #0a0a0a;
}

/* Match any art-info widget */
Static.-art-info {
    height: auto;
    width: 100%;
    text-align: center;
    padding: 1;
    background: #151515;
    border-bottom: solid #2a2a2a;
}

/* Match any art-image widget */
Image.-art-image {
    width: auto;
    height: 1fr;
    min-height: 15;
    content-align: center middle;
}

/* ─── Rulings Scroll ─── */
TabPane.-tab-rulings VerticalScroll {
    scrollbar-color: #c9a227;
}

/* ─── Synergy Panel ─── */
#synergy-panel {
    height: 12%;
    max-height: 5;
    padding: 0 1;
    display: none;
    border-top: heavy #c9a227;
    background: #1a1a2e;
    overflow-y: auto;
}

#synergy-panel.visible {
    display: block;
}

#synergy-content {
    background: #1a1a2e;
    height: auto;
}

/* ─── Input: Command Line ─── */
#input-bar {
    width: 100%;
    height: 3;
    padding: 0 2;
    background: #0a0a14;
    border-top: heavy #c9a227;
}

#input-bar Label {
    color: #c9a227;
    width: auto;
    padding: 0 1 0 0;
}

#search-input {
    width: 1fr;
    background: #1a1a2e;
    border: tall #3d3d3d;
    color: #e0e0e0;
}

#search-input:focus {
    border: tall #c9a227;
    background: #1e1e32;
}

/* ─── Footer ─── */
Footer {
    background: #0a0a0a;
    color: #555;
    height: 1;
}

Footer > .footer--key {
    background: #1a1a2e;
    color: #c9a227;
}

Footer > .footer--description {
    color: #666;
}

/* ─── Rarity Colors (for use in rich text) ─── */
/* Common: #1a1a1a (dark) */
/* Uncommon: #c0c0c0 (silver) */
/* Rare: #c9a227 (gold) */
/* Mythic: #e65c00 (orange-red) */

/* ─── Mana Colors ─── */
/* White: #f9faf4 */
/* Blue: #0e68ab */
/* Black: #150b00 */
/* Red: #d3202a */
/* Green: #00733e */

/* ─── Deck Panel ─── */
#deck-panel {
    width: 0;
    height: 100%;
    display: none;
    background: #121212;
    border-right: solid #3d3d3d;
}

#deck-panel.visible {
    width: 30;
    display: block;
}

#deck-list-header {
    height: 3;
    background: #1a1a1a;
    border-bottom: solid #3d3d3d;
    padding: 0 1;
    content-align: center middle;
}

#new-deck-btn {
    margin: 1;
    width: 100%;
}

#deck-list {
    height: 1fr;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

#deck-list > ListItem {
    padding: 0 1;
    height: auto;
    border-bottom: solid #1a1a1a;
}

#deck-list > ListItem:hover {
    background: #1a1a2e;
}

#deck-list > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

#deck-list-footer {
    height: 2;
    padding: 0 1;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
}
"""
