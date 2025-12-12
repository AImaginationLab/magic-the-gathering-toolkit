"""CSS styles for the MTG Spellbook TUI."""

APP_CSS = """
Screen {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 2fr;
    grid-rows: auto 1fr auto;
}

#header {
    column-span: 2;
    height: 3;
    background: $primary-darken-2;
    padding: 0 1;
    content-align: center middle;
}

#header-content {
    text-align: center;
}

#menu {
    height: 100%;
    background: $surface;
    padding: 1;
    border-right: solid $primary;
    width: 100%;
}

#menu-title {
    text-style: bold;
    color: $warning;
    margin-bottom: 1;
}

.menu-section {
    margin-top: 1;
    color: $text-muted;
}

.menu-item {
    padding: 0 1;
}

#content {
    height: 100%;
    padding: 0;
}

#results-container {
    width: 40%;
    height: 100%;
    border-right: solid $primary-darken-1;
}

#results-header {
    height: 3;
    background: $surface;
    padding: 0 1;
    content-align: left middle;
}

#results-list {
    height: 100%;
}

#results-list > ListItem {
    padding: 0 1;
}

#results-list > ListItem:hover {
    background: $primary-darken-1;
}

#results-list > ListItem.-highlight {
    background: $primary;
}

#detail-container {
    width: 60%;
    height: 100%;
}

#card-panel {
    height: 100%;
    padding: 0;
}

/* When synergy panel is visible, card panel takes 60% */
#card-panel.synergy-mode {
    height: 60%;
}

#card-tabs {
    height: 100%;
}

TabPane {
    padding: 1;
}

#tab-art {
    layout: vertical;
    align: center middle;
}

#art-info {
    height: auto;
    width: 100%;
    text-align: center;
    margin-bottom: 1;
}

#art-image {
    width: auto;
    height: 1fr;
    min-height: 15;
    content-align: center middle;
}

#synergy-panel {
    height: 40%;
    padding: 1;
    display: none;
    border-top: solid $primary;
    background: $surface;
}

#synergy-panel.visible {
    display: block;
}

#input-bar {
    column-span: 2;
    height: 3;
    padding: 0 1;
    background: $surface;
}

#search-input {
    width: 100%;
}

#status-bar {
    column-span: 2;
    height: 1;
    background: $primary-darken-3;
    color: $text-muted;
    padding: 0 1;
}
"""
