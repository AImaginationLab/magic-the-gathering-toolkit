"""CSS styles for the MTG Spellbook TUI."""

APP_CSS = """
/* ═══════════════════════════════════════════════════════════
   MTG SPELLBOOK - Enhanced Card Frame Design
   ═══════════════════════════════════════════════════════════ */

Screen {
    background: #0d0d0d;
    overflow: hidden;  /* Prevent screen from scrolling - only content should scroll */
}

/* Main app screen layout (MTGSpellbook) - NOT for BaseScreen subclasses
   BaseScreen has its own grid layout defined in screens/base.py */
MTGSpellbook {
    layout: grid;
    grid-size: 1;
    grid-rows: 5 auto 1fr 1;  /* header (5), menu (auto), content (1fr), footer (1) */
}

.hidden {
    display: none;
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
}

/* ─── Results: Enhanced Card Stack ─── */
#results-container {
    width: 40;
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

#card-comparison-container.hidden {
    display: none;
}

#card-panel {
    width: 100%;
    height: 100%;
    background: #151515;
    border: round #3d3d3d;
    margin: 0 1;
}

#card-panel:focus-within {
    border: round #e6c84a;
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

/* ─── Synergy Layout Mode (synergy list on top, cards side-by-side below) ─── */
#main-container.synergy-layout {
    layout: vertical;
}

#main-container.synergy-layout #deck-panel {
    display: none;
}

#main-container.synergy-layout #collection-panel {
    display: none;
}

#main-container.synergy-layout #synergy-panel {
    display: block;
    height: 35%;
    min-height: 10;
    width: 100%;
}

#main-container.synergy-layout #detail-container {
    height: 65%;
    width: 100%;
}

#main-container.synergy-layout #card-panel.synergy-mode {
    width: 50%;
    height: 100%;
}

#main-container.synergy-layout #source-card-panel.visible {
    width: 50%;
    height: 100%;
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
    background: #151515;
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

/* ─── Enhanced Synergy Panel ─── */
#synergy-panel {
    width: 35%;
    min-width: 40;
    height: 100%;
    padding: 0;
    display: block;
    border-right: heavy #c9a227;
    background: #0d0d0d;
}

#synergy-panel.hidden {
    display: none;
}

.synergy-panel-container {
    width: 100%;
    height: 100%;
}

.synergy-panel-header {
    height: 4;
    background: #1a1a2e;
    border-bottom: heavy #c9a227;
    padding: 0 2;
    align: left middle;
}

.synergy-panel-title {
    width: auto;
    padding: 0 2 0 0;
}

.synergy-search {
    width: 1fr;
    background: #1a1a2e;
    border: tall #3d3d3d;
}

.synergy-search:focus {
    border: tall #c9a227;
    background: #1e1e32;
}

/* Type filter pills (horizontal) */
.type-index-pills {
    height: 2;
    padding: 0 2;
    background: #151515;
    border-bottom: solid #3d3d3d;
}

.synergy-list {
    width: 100%;
    height: 1fr;
    background: #0d0d0d;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

.synergy-list > ListItem {
    padding: 0 1;
    height: 2;
    border-bottom: solid #1a1a1a;
    background: #121212;
}

.synergy-list > ListItem:hover {
    background: #1a1a2e;
    border-left: solid #5a5a6e;
}

.synergy-list > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

.synergy-item-content {
    width: 100%;
    height: auto;
}

.synergy-statusbar {
    height: 2;
    padding: 0 2;
    background: #0a0a14;
    color: #666666;
    content-align: left middle;
}

/* ─── Search Input in Results Pane ─── */
#results-container > #search-input {
    width: 100%;
    height: 3;
    margin: 0 0 1 0;
    background: #1a1a2e;
    border: tall #3d3d3d;
    color: #e0e0e0;
}

#results-container > #search-input:focus {
    border: tall #c9a227;
    background: #1e1e32;
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

/* ─── Collection Panel ─── */
#collection-panel {
    width: 0;
    height: 100%;
    display: none;
    background: #0a0a14;
    border-right: heavy #c9a227;
}

#collection-panel.visible {
    width: 50;
    display: block;
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

/* ─── Gallery View Components ─── */
/* Vertical layout: preview on top, filmstrip on bottom */
.gallery-container {
    width: 100%;
    height: 1fr;
    layout: vertical;
}

/* Filmstrip: horizontal scrolling strip of thumbnails at bottom */
.printings-filmstrip {
    width: 100%;
    height: 18;
    min-height: 18;
    background: #0a0a0a;
    border-top: solid #3d3d3d;
    padding: 0 1;
}

/* Container for filmstrip cards */
.filmstrip-container {
    width: auto;
    height: 100%;
    padding: 0 1;
}

/* Filmstrip thumbnail card - image + set/rarity + price */
.shop-card {
    width: 18;
    height: 16;
    background: #151515;
    border: round #2a2a2a;
    margin: 0 1 0 0;
    padding: 0;
}

.shop-card:hover {
    background: #1a1a2e;
    border: round #4d4d4d;
}

.shop-card.selected {
    background: #1e1e2e;
    border: heavy #e6c84a;
}

.shop-card.in-compare {
    border: heavy #4a9eff;
}

/* Thumbnail image in filmstrip card */
.shop-card-thumb {
    width: 100%;
    height: 12;
    content-align: center middle;
}

.shop-card-thumb-placeholder {
    width: 100%;
    height: 12;
    content-align: center middle;
    background: #1a1a1a;
}

/* Set code + rarity icon in filmstrip */
.shop-card-set {
    width: 100%;
    height: 1;
    text-align: center;
    content-align: center middle;
}

/* Price in filmstrip */
.shop-card-price {
    width: 100%;
    height: 1;
    text-align: center;
    content-align: center middle;
}

/* Legacy thumbnail support (kept for compatibility) */
.thumbnail-card {
    width: 15;
    height: 6;
    background: #151515;
    border: round #2a2a2a;
    margin: 0 1 1 0;
    padding: 1;
    content-align: center middle;
}

.thumbnail-card:hover {
    background: #1a1a2e;
    border: round #3d3d3d;
}

.thumbnail-card.selected {
    background: #1e1e2e;
    border: heavy #e6c84a;
}

.thumbnail-set {
    text-align: center;
    width: 100%;
    height: auto;
}

.thumbnail-price {
    text-align: center;
    width: 100%;
    height: auto;
    text-style: bold;
}

.price-low {
    color: #888;
}

.price-medium {
    color: #e6c84a;
}

.price-medium-high {
    color: #ff9500;
}

.price-high {
    color: #e65c00;
}

/* Large preview panel - takes up main area above filmstrip */
.preview-panel {
    width: 100%;
    height: 1fr;
    background: #151515;
    padding: 1 2;
    align: center middle;
}

#preview-image {
    width: auto;
    height: auto;
}

.preview-info {
    width: 100%;
    height: auto;
    padding: 1 0;
    text-align: left;
}

/* ─── View Mode Toggle ─── */
.view-toggle {
    width: 100%;
    height: 3;
    background: #0a0a14;
    border-bottom: solid #3d3d3d;
    layout: horizontal;
    align: center middle;
}

.mode-button {
    width: auto;
    height: auto;
    padding: 0 2;
    margin: 0 1;
    text-align: center;
    color: #666;
}

.mode-button.mode-active {
    color: #e6c84a;
    text-style: bold underline;
}

.mode-button.mode-inactive {
    color: #666;
}

.mode-button.mode-disabled {
    color: #333;
}

/* ─── Gallery / Focus View Switching ─── */
.gallery-container.gallery-hidden {
    display: none;
}

.focus-view {
    width: 100%;
    height: 1fr;
    background: #151515;
}

.focus-view.focus-hidden {
    display: none;
}

/* ─── Focus View Components ─── */
.focus-main-container {
    width: 100%;
    height: 1fr;
    layout: horizontal;
}

.focus-image-container {
    width: 40%;
    height: 100%;
    min-height: 24;
    max-height: 90%;
    background: #151515;
    content-align: center middle;
    align: center middle;
    padding: 1 2;
}

#focus-image {
    width: 100%;
    height: auto;
    min-height: 20;
    max-height: 35;
    content-align: center middle;
}

.focus-no-image {
    width: 100%;
    height: 100%;
    content-align: center middle;
    color: #666;
}

.focus-metadata {
    width: 50%;
    height: 100%;
    background: #151515;
    border-left: solid #3d3d3d;
    padding: 1 2;
    overflow-y: auto;
}

.focus-card-name {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 0 0 1 0;
}

.focus-mana-cost {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 0 0 1 0;
    color: #b8860b;
}

.focus-type-line {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 0 0 1 0;
    color: #aaa;
}

.focus-set-info {
    width: 100%;
    height: auto;
    text-align: left;
    color: #888;
    padding: 0 0 1 0;
}

.focus-artist {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 0 0 1 0;
}

.focus-artist:hover {
    background: #1a1a2e;
}

.focus-oracle-text {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 1 0;
    color: #ccc;
}

.focus-legalities {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 1 0 0 0;
}

.focus-flavor {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 1 0;
}

.focus-prices {
    width: 100%;
    height: auto;
    text-align: left;
    padding: 1 0;
}

.focus-nav-counter {
    width: 100%;
    height: auto;
    text-align: center;
    padding: 2 0 0 0;
    color: #e6c84a;
}

.focus-statusbar {
    width: 100%;
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

.art-statusbar {
    width: 100%;
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

.gallery-statusbar {
    width: 100%;
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

/* ─── Compare View Components ─── */
.compare-view {
    width: 100%;
    height: 1fr;
    background: #151515;
}

.compare-view.compare-hidden {
    display: none;
}

.compare-header {
    display: none;
}

.compare-slots-container {
    width: 100%;
    height: 1fr;
    layout: horizontal;
    align: center top;
    padding: 0;
}

.compare-slot {
    width: 1fr;
    height: 100%;
    background: #151515;
    border: none;
    margin: 0;
    padding: 0;
    content-align: center top;
}

.compare-image {
    width: auto;
    height: 1fr;
    content-align: center middle;
}

.compare-no-image {
    width: 100%;
    height: 1fr;
    content-align: center middle;
    color: #666;
}

.compare-metadata {
    width: 100%;
    height: 1;
    padding: 0;
    background: #151515;
    text-align: center;
    content-align: center middle;
}

.compare-summary {
    width: 100%;
    height: 1;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

.compare-statusbar {
    width: 100%;
    height: 1;
    background: #1a1a1a;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

.thumbnail-card.in-compare {
    border: heavy #7ec850;
}

/* ─── Loading Indicator ─── */
.art-loading {
    width: 100%;
    height: 5;
    background: #151515;
    content-align: center middle;
}

.art-loading.hidden {
    display: none;
}

/* ─── Sort Order Indicator ─── */
.sort-indicator {
    color: #e6c84a;
    text-style: bold;
}

/* ─── Compare Slot Selection ─── */
.compare-slot.selected {
    border: heavy #e6c84a;
}

/* ─── Navigation Boundary Flash ─── */
.boundary-flash {
    background: #3a2020;
}

/* ─── Clickable Mode Buttons ─── */
.mode-button:hover {
    background: #1a1a2e;
    color: #c9a227;
}

/* ─── Artist Portfolio View ─── */
.portfolio-main {
    width: 100%;
    height: 1fr;
    layout: horizontal;
}

.portfolio-gallery {
    width: 45%;
    height: 100%;
    background: #0d0d0d;
}

.portfolio-preview {
    width: 25%;
    height: 100%;
    background: #151515;
    border-left: solid #3d3d3d;
    padding: 1 2;
}

.portfolio-stats {
    width: 30%;
    height: 100%;
    background: #151515;
    padding: 1 2;
    border-left: solid #3d3d3d;
}

.portfolio-statusbar {
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

/* Artist Stats Panel */
.stats-artist-name {
    height: auto;
    padding: 0 0 1 0;
    text-align: center;
}

.stats-row {
    height: auto;
    padding: 0 0 0 0;
}

.stats-section-header {
    height: auto;
    padding: 1 0 0 0;
}

.stats-formats-scroll {
    height: auto;
    max-height: 10;
}

.stats-formats {
    height: auto;
}

/* Artist Gallery */
.gallery-list {
    height: 100%;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

/* CardResultItem in gallery list - unified two-line format */
#gallery-list > CardResultItem {
    padding: 0 1;
    height: auto;
    min-height: 3;
    border-bottom: solid #1a1a1a;
    background: #121212;
}

#gallery-list > CardResultItem:hover {
    background: #1a1a2e;
}

#gallery-list > CardResultItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

/* Card Preview Panel */
.preview-card-name {
    height: auto;
    padding: 0 0 1 0;
}

.preview-mana-cost {
    height: auto;
}

.preview-type {
    height: auto;
    padding: 0 0 1 0;
}

.preview-set-info {
    height: auto;
    padding: 0 0 1 0;
}

.preview-details-scroll {
    height: 1fr;
}

.preview-keywords {
    height: auto;
}

.preview-price {
    height: auto;
}

.preview-hint {
    height: 2;
    text-align: center;
    color: #666;
    padding: 1 0 0 0;
}

/* Set Detail View */
.set-detail-main {
    width: 100%;
    height: 1fr;
    layout: horizontal;
}

.set-info-panel {
    width: 30%;
    height: 100%;
    background: #151515;
    padding: 1 2;
    border-right: solid #3d3d3d;
    overflow-y: auto;
}

.set-info-content {
    height: auto;
}

.set-info-text {
    height: auto;
}

.set-card-list {
    width: 45%;
    height: 100%;
    background: #0d0d0d;
    border-right: solid #3d3d3d;
}

.card-list-scroll {
    height: 100%;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

.card-list-empty {
    padding: 2;
    text-align: center;
}

.card-list-view {
    height: 100%;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

.card-list-view > ListItem {
    padding: 0 1;
    height: auto;
    border-bottom: solid #1a1a1a;
    background: #121212;
}

.card-list-view > ListItem:hover {
    background: #1a1a2e;
    border-left: solid #5a5a6e;
}

.card-list-view > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

.set-card-preview {
    width: 25%;
    height: 100%;
    background: #151515;
    padding: 1 2;
    overflow-y: auto;
}

.card-preview-text {
    height: auto;
}

.set-statusbar {
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

/* Rarity indicator colors (for card list) */
.rarity-mythic {
    color: #e65c00;
}

.rarity-rare {
    color: #c9a227;
}

.rarity-uncommon {
    color: #c0c0c0;
}

.rarity-common {
    color: #888;
}

/* ─── Empty State Styling ─── */
.empty-state {
    padding: 4 2;
    text-align: center;
    color: #666;
    background: #0d0d0d;
}

/* ─── Deck Editor Panel ─── */
#deck-editor-container {
    width: 100%;
    height: 100%;
    display: none;
}

#deck-editor-container.visible {
    display: block;
}

.deck-editor-panel {
    width: 100%;
    height: 100%;
    background: #0d0d0d;
}

.deck-editor-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: heavy #c9a227;
    padding: 0 1;
    content-align: center middle;
    color: #e6c84a;
    text-style: bold;
}

.deck-cards-container {
    width: 60%;
    height: 100%;
    background: #0f0f0f;
    border-right: solid #3d3d3d;
}

.deck-section-header {
    height: 2;
    padding: 0 1;
    background: #1a1a1a;
    border-bottom: solid #3d3d3d;
}

.deck-card-list {
    height: 1fr;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

.deck-card-list > ListItem {
    padding: 0 1;
    height: auto;
    border-bottom: solid #1a1a1a;
    background: #121212;
}

.deck-card-list > ListItem:hover {
    background: #1a1a2e;
    border-left: solid #5a5a6e;
}

.deck-card-list > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

/* ─── Deck Stats Panel ─── */
.deck-stats-container {
    width: 40%;
    height: 100%;
    background: #151515;
    padding: 1;
    overflow-y: auto;
}

.deck-stats-panel {
    width: 100%;
    height: auto;
    padding: 0 1;
    background: #1a1a1a;
}

.stats-section {
    height: auto;
    margin-bottom: 1;
}

.stats-header {
    text-style: bold;
    color: #c9a227;
    margin-bottom: 0;
}

.stats-row {
    height: auto;
}

.mana-curve-bar {
    color: #e6c84a;
}

.card-type-row {
    height: auto;
}

.deck-editor-footer {
    height: 2;
    padding: 0 1;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
}

/* ─── Dashboard Landing Page V4 (Interactive) ─── */
#dashboard.hidden {
    display: none;
}

.dashboard-view {
    width: 100%;
    height: 100%;
}

/* ─── Artist Browser Widget ─── */
.artist-browser-overlay {
    width: 100%;
    height: 100%;
    background: #0d0d0d;
    layer: overlay;
}

.artist-browser-container {
    width: 100%;
    height: 100%;
}

.artist-browser-header {
    height: 4;
    background: #1a1a2e;
    border-bottom: heavy #c9a227;
    padding: 0 2;
    align: left middle;
}

.artist-browser-title {
    width: auto;
    padding: 0 2 0 0;
}

.artist-search {
    width: 30;
    background: #151515;
    border: tall #3d3d3d;
}

.artist-search:focus {
    border: tall #c9a227;
    background: #1e1e32;
}

.artist-browser-content {
    width: 100%;
    height: 1fr;
}

.letter-index-container {
    width: 8;
    height: 100%;
    background: #151515;
    border-right: solid #3d3d3d;
    padding: 1;
}

.letter-index {
    height: auto;
}

.artist-list {
    width: 1fr;
    height: 100%;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

.artist-list > ListItem {
    padding: 0 1;
    height: auto;
    border-bottom: solid #1a1a1a;
    background: #121212;
}

.artist-list > ListItem:hover {
    background: #1a1a2e;
}

.artist-list > ListItem.-highlight {
    background: #2a2a4e;
    border-left: heavy #c9a227;
}

.letter-header-item {
    background: #1a1a2e;
    padding: 0 1;
    margin-top: 1;
}

.letter-header {
    height: auto;
}

.artist-item {
    padding: 0 2;
}

.artist-item-content {
    height: auto;
}

.artist-statusbar {
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

/* ─── Block Browser Widget ─── */
.block-browser-overlay {
    width: 100%;
    height: 100%;
    background: #0d0d0d;
    layer: overlay;
}

.block-browser-container {
    width: 100%;
    height: 100%;
}

.block-browser-title {
    height: 3;
    background: #1a1a2e;
    border-bottom: heavy #c9a227;
    padding: 0 2;
    content-align: center middle;
}

.block-browser-content {
    width: 100%;
    height: 1fr;
}

.block-tree-container {
    width: 60%;
    height: 100%;
    background: #0d0d0d;
    border-right: solid #3d3d3d;
}

.block-tree {
    width: 100%;
    height: 100%;
    scrollbar-color: #c9a227;
    scrollbar-color-hover: #e6c84a;
}

Tree {
    background: #0d0d0d;
}

Tree > .tree--cursor {
    background: #2a2a4e;
    color: #e6c84a;
}

Tree > .tree--guides {
    color: #3d3d3d;
}

Tree > .tree--guides-hover {
    color: #c9a227;
}

.block-info-container {
    width: 40%;
    height: 100%;
    background: #151515;
    padding: 1 2;
}

.block-info {
    height: auto;
}

.block-statusbar {
    height: 2;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}

.compare-slot.selected {
    border: heavy #e6c84a;
}

.compare-slot-header {
    height: 3;
    background: #1a1a2e;
    border-bottom: solid #3d3d3d;
    padding: 1;
    content-align: center middle;
}

.compare-slot-content {
    height: 1fr;
    padding: 2;
}

.compare-slot-body {
    height: auto;
}

.compare-decision {
    height: auto;
    min-height: 10;
    background: #1a1a1a;
    border-top: solid #3d3d3d;
    padding: 2;
}

.compare-statusbar {
    height: 3;
    background: #0a0a0a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 1 2;
    content-align: center middle;
}

.synergy-statusbar {
    height: 2;
    background: #0a0a0a;
    border-top: solid #3d3d3d;
    text-align: center;
    padding: 0;
    content-align: center middle;
}
"""
