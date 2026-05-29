#!/bin/bash
set -e

echo "🗑️  Uninstalling ios-simulator-mcp..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to remove MCP server from JSON config
remove_mcp_server() {
    local config_file="$1"

    if [ ! -f "$config_file" ]; then
        return 0
    fi

    if ! grep -q '"ios-simulator"' "$config_file" 2>/dev/null; then
        return 0
    fi

    # Remove the MCP server configuration using Python
    python3 - "$config_file" << 'PYTHON_SCRIPT'
import json
import sys

config_file = sys.argv[1]

try:
    with open(config_file, 'r') as f:
        config = json.load(f)

    if 'mcpServers' in config and 'ios-simulator' in config['mcpServers']:
        del config['mcpServers']['ios-simulator']

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            f.write('\n')

        print("  ✓ Configuration removed")
    else:
        print("  No configuration found")
except Exception as e:
    print(f"  Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT
}

# Remove from Claude Code
CLAUDE_CODE_CONFIG="$HOME/.claude/settings.json"
if [ -f "$CLAUDE_CODE_CONFIG" ]; then
    echo -e "${BLUE}Removing from Claude Code...${NC}"
    remove_mcp_server "$CLAUDE_CODE_CONFIG"
fi

# Remove from Claude Desktop
CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CLAUDE_DESKTOP_CONFIG" ]; then
    echo -e "${BLUE}Removing from Claude Desktop...${NC}"
    remove_mcp_server "$CLAUDE_DESKTOP_CONFIG"
fi

# Remove from Cursor
CURSOR_CONFIG="$HOME/.cursor/mcp_config.json"
CURSOR_ALT_CONFIG="$HOME/Library/Application Support/Cursor/User/globalStorage/mcp_config.json"

if [ -f "$CURSOR_CONFIG" ]; then
    echo -e "${BLUE}Removing from Cursor...${NC}"
    remove_mcp_server "$CURSOR_CONFIG"
elif [ -f "$CURSOR_ALT_CONFIG" ]; then
    echo -e "${BLUE}Removing from Cursor...${NC}"
    remove_mcp_server "$CURSOR_ALT_CONFIG"
fi

# Uninstall the package
echo -e "${BLUE}Uninstalling package...${NC}"
if command -v uv &> /dev/null; then
    uv tool uninstall ios-simulator-mcp 2>/dev/null || true
    echo -e "${GREEN}✓ Package uninstalled${NC}"
elif command -v pip &> /dev/null; then
    pip uninstall -y ios-simulator-mcp 2>/dev/null || true
    echo -e "${GREEN}✓ Package uninstalled${NC}"
fi

echo ""
echo -e "${GREEN}✅ Uninstallation complete!${NC}"
echo -e "${YELLOW}Please restart Claude Desktop or Cursor if they are running.${NC}"
echo ""
