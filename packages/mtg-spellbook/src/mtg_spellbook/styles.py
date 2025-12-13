"""CSS styles for the MTG Spellbook TUI."""

APP_CSS = """
/* ═══════════════════════════════════════════════════════════
   MTG SPELLBOOK - Enhanced Card Frame Design
   ═══════════════════════════════════════════════════════════ */

Screen {
    background: #0d0d0d;
    layout: grid;
    grid-size: 1;
    grid-rows: auto 1fr auto auto;
}

/* ─── Header: Enhanced Banner ─── */
#header-content {
    width: 100%;
    height: 5;
    background: #0a0a14;
    border-bottom: heavy #c9a227;
    padding: 1 2;
    content-align: center middle;
    text-align: center;
    color: #e6c84a;
}

/* ─── Main Layout ─── */
#main-container {
    width: 100%;
    height: 100%;
}

/* ─── Results: Enhanced Card Stack ─── */
#results-container {
    width: 35;
    height: 100%;
    background: #0f0f0f;
    border-right: solid #3d3d3d;
}

#results-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: solid #c9a227;
    padding: 0 1;
    content-align: center middle;
    color: #e6c84a;
    text-style: bold;
}

#results-list {
    height: 100%;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
    scrollbar-color-active: #fff8dc;
}

/* Enhanced list items with better hover */
#results-list > ListItem {
    padding: 0 1;
    height: auto;
    border-bottom: solid #1a1a1a;
    background: #121212;
}

#results-list > ListItem:hover {
    background: #1a1a2e;
    border-left: solid #5a5a6e;
}

#results-list > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

/* Enhanced highlight on hover */
#results-list > ListItem.-highlight:hover {
    background: #2e2e58;
    border-left: heavy #e6c84a;
}

/* ─── Card Panel: Enhanced Display ─── */
#detail-container {
    height: 100%;
    background: #0d0d0d;
}

#card-comparison-container {
    width: 100%;
    height: 100%;
}

#card-panel {
    width: 100%;
    height: 100%;
    background: #151515;
    border: round #3d3d3d;
    margin: 0 1;
}

#card-panel.synergy-mode {
    width: 50%;
    height: 100%;
}

/* ─── Source Card Panel (Synergy Mode) ─── */
#source-card-panel {
    width: 0;
    height: 100%;
    display: none;
    background: #151515;
    border: round #3d3d3d;
    border-left: heavy #c9a227;
    margin: 0 1 0 0;
}

#source-card-panel.visible {
    width: 50%;
    display: block;
}

#source-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: heavy #c9a227;
    padding: 0 1;
    content-align: center middle;
    color: #e6c84a;
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

/* ─── Tabs: Enhanced Navigation ─── */
#card-tabs {
    height: 100%;
}

Tabs {
    background: #1a1a1a;
    border-bottom: solid #3d3d3d;
}

/* Enhanced tab styling */
Tab {
    background: #1a1a1a;
    color: #777;
    padding: 0 2;
    border-right: solid #252525;
}

Tab:hover {
    background: #252525;
    color: #bbb;
}

Tab.-active {
    background: #1e1e2e;
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

*:focus {
    text-style: none;
}

TabPane:focus-within {
    background: #151515;
}

/* ─── Card Text Area ─── */
Static.-card-text {
    background: #151515;
}

/* ─── Art Gallery ─── */
TabPane.-tab-art {
    layout: vertical;
    align: center middle;
    background: #0a0a0a;
}

Static.-art-info {
    height: auto;
    width: 100%;
    text-align: center;
    padding: 1;
    background: #151515;
    border-bottom: solid #2a2a2a;
}

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

/* ─── Input: Enhanced Command Line ─── */
#input-bar {
    width: 100%;
    height: 3;
    padding: 0 2;
    background: #0a0a14;
    border-top: heavy #c9a227;
}

#input-bar Label {
    color: #e6c84a;
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
    color: #ffffff;
}

/* ─── Footer: Enhanced ─── */
Footer {
    background: #0a0a0a;
    color: #666;
    height: 1;
}

Footer > .footer--key {
    background: #1a1a2e;
    color: #e6c84a;
    text-style: bold;
}

Footer > .footer--description {
    color: #777;
}

/* ─── Deck Panel: Enhanced "Binder" Aesthetic ─── */
#deck-panel {
    width: 0;
    height: 100%;
    display: none;
    background: #0a0a14;
    border-right: heavy #c9a227;
}

#deck-panel.visible {
    width: 30;
    display: block;
}

#deck-list-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: heavy #c9a227;
    padding: 0 1;
    content-align: center middle;
    color: #e6c84a;
    text-style: bold;
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

/* Enhanced deck list items */
#deck-list > ListItem {
    padding: 0 1;
    height: auto;
    border-bottom: solid #1a1a1a;
    background: #121218;
    margin: 0 1;
}

#deck-list > ListItem:hover {
    background: #1a1a2e;
    border: solid #5a5a6e;
    margin: 0;
    padding: 0 2;
}

#deck-list > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
    margin: 0;
    padding: 0 2;
}

#deck-list-footer {
    height: 2;
    padding: 0 1;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
}

/* ─── Enhanced Buttons (for modals) ─── */
Button {
    background: #2a2a4e;
    color: #e0e0e0;
    border: solid #3d3d3d;
}

Button:hover {
    background: #3a3a5e;
    color: #ffffff;
    border: solid #5d5d7d;
}

Button:focus {
    border: heavy #c9a227;
    text-style: bold;
}

Button.-primary {
    background: #c9a227;
    color: #0d0d0d;
    border: solid #e6c84a;
    text-style: bold;
}

Button.-primary:hover {
    background: #e6c84a;
    color: #000000;
}

/* ─── Enhanced Focus States ─── */
ListView:focus ListItem.-highlight {
    background: #3a3a6e;
    border-left: heavy #e6c84a;
}
"""
