"""
UI 컴포넌트 패키지

재사용 가능한 UI 컴포넌트를 제공합니다.
"""

from oracle_duckdb_sync.ui.components.breadcrumb import render_breadcrumb, get_page_title
from oracle_duckdb_sync.ui.components.favorites import (
    initialize_favorites,
    add_favorite,
    remove_favorite,
    is_favorite,
    toggle_favorite,
    render_favorites_section,
    render_favorite_button
)
from oracle_duckdb_sync.ui.components.recent_pages import (
    initialize_recent_pages,
    add_recent_page,
    get_recent_pages,
    render_recent_pages_section,
    clear_recent_pages
)
from oracle_duckdb_sync.ui.components.search import (
    get_searchable_pages,
    search_pages,
    render_search_box
)
from oracle_duckdb_sync.ui.components.shortcuts import (
    get_shortcut_config,
    render_keyboard_shortcuts,
    handle_keyboard_shortcut,
    render_shortcuts_help,
    initialize_shortcuts
)

__all__ = [
    # Breadcrumb
    'render_breadcrumb',
    'get_page_title',
    # Favorites
    'initialize_favorites',
    'add_favorite',
    'remove_favorite',
    'is_favorite',
    'toggle_favorite',
    'render_favorites_section',
    'render_favorite_button',
    # Recent Pages
    'initialize_recent_pages',
    'add_recent_page',
    'get_recent_pages',
    'render_recent_pages_section',
    'clear_recent_pages',
    # Search
    'get_searchable_pages',
    'search_pages',
    'render_search_box',
    # Shortcuts
    'get_shortcut_config',
    'render_keyboard_shortcuts',
    'handle_keyboard_shortcut',
    'render_shortcuts_help',
    'initialize_shortcuts'
]
