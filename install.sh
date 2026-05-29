#!/bin/bash
set -e

echo "🚀 Installing ios-simulator-mcp..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This tool requires macOS (iOS Simulator is only available on macOS)${NC}"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}Installing uv (Python package installer)...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install the package
echo -e "${BLUE}Installing ios-simulator-mcp package...${NC}"
uv tool install ios-simulator-mcp
echo -e "${GREEN}✓ Package installed${NC}"
echo ""

# Function to add MCP server to JSON config
add_mcp_server() {
    local config_file="$1"
    local config_dir=$(dirname "$config_file")

    # Create directory if it doesn't exist
    mkdir -p "$config_dir"

    # Create config file if it doesn't exist
    if [ ! -f "$config_file" ]; then
        echo '{}' > "$config_file"
    fi

    # Check if ios-simulator is already configured
    if grep -q '"ios-simulator"' "$config_file" 2>/dev/null; then
        echo -e "${YELLOW}  ios-simulator already configured, skipping...${NC}"
        return 0
    fi

    # Add the MCP server configuration using Python
    python3 - "$config_file" << 'PYTHON_SCRIPT'
import json
import sys

config_file = sys.argv[1]

try:
    with open(config_file, 'r') as f:
        config = json.load(f)
except:
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['ios-simulator'] = {
    'command': 'uvx',
    'args': ['ios-simulator-mcp']
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

print("  ✓ Configuration added")
PYTHON_SCRIPT
}

# Configure Claude Code
CLAUDE_CODE_CONFIG="$HOME/.claude/settings.json"
if [ -d "$HOME/.claude" ] || [ -f "$CLAUDE_CODE_CONFIG" ]; then
    echo -e "${BLUE}Configuring Claude Code...${NC}"
    add_mcp_server "$CLAUDE_CODE_CONFIG"
else
    echo -e "${YELLOW}Claude Code not found, skipping...${NC}"
fi

# Configure Claude Desktop
CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -d "$HOME/Library/Application Support/Claude" ] || [ -f "$CLAUDE_DESKTOP_CONFIG" ]; then
    echo -e "${BLUE}Configuring Claude Desktop...${NC}"
    add_mcp_server "$CLAUDE_DESKTOP_CONFIG"
    echo -e "${YELLOW}  Please restart Claude Desktop for changes to take effect${NC}"
else
    echo -e "${YELLOW}Claude Desktop not found, skipping...${NC}"
fi

# Configure Cursor
CURSOR_CONFIG="$HOME/.cursor/mcp_config.json"
CURSOR_ALT_CONFIG="$HOME/Library/Application Support/Cursor/User/globalStorage/mcp_config.json"

cursor_configured=false
if [ -d "$HOME/.cursor" ]; then
    echo -e "${BLUE}Configuring Cursor...${NC}"
    add_mcp_server "$CURSOR_CONFIG"
    cursor_configured=true
elif [ -d "$HOME/Library/Application Support/Cursor" ]; then
    echo -e "${BLUE}Configuring Cursor...${NC}"
    mkdir -p "$(dirname "$CURSOR_ALT_CONFIG")"
    add_mcp_server "$CURSOR_ALT_CONFIG"
    cursor_configured=true
fi

if [ "$cursor_configured" = true ]; then
    echo -e "${YELLOW}  Please restart Cursor for changes to take effect${NC}"
else
    echo -e "${YELLOW}Cursor not found, skipping...${NC}"
fi

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo -e "${BLUE}Available tools:${NC}"
echo "  • list_simulators - List all iOS simulators"
echo "  • take_screenshot - Capture simulator screen"
echo "  • tap - Tap at coordinates"
echo "  • swipe - Swipe gesture"
echo "  • launch_app - Launch apps"
echo "  • get_logs - View system logs"
echo "  • And 15+ more tools!"
echo ""
echo -e "${BLUE}Documentation:${NC} https://github.com/adborroto/ios-simulator-mcp"
echo ""
