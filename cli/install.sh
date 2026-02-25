#!/bin/sh
# AI SDK CLI Installer
# https://github.com/open-metadata/ai-sdk
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/open-metadata/ai-sdk/main/cli/install.sh | sh
#
# This script detects your OS and architecture, downloads the appropriate
# binary from GitHub releases, and installs it to a location in your PATH.

set -e

# Colors for output (disabled if not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# Configuration
GITHUB_REPO="open-metadata/ai-sdk"
BINARY_NAME="ai-sdk"
INSTALL_DIR_PRIMARY="$HOME/.local/bin"
INSTALL_DIR_FALLBACK="/usr/local/bin"

# Print functions
info() {
    printf "${BLUE}==>${NC} %s\n" "$1"
}

success() {
    printf "${GREEN}==>${NC} %s\n" "$1"
}

warn() {
    printf "${YELLOW}Warning:${NC} %s\n" "$1"
}

error() {
    printf "${RED}Error:${NC} %s\n" "$1" >&2
}

# Cleanup function for temp files
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Detect operating system
detect_os() {
    OS="$(uname -s)"
    case "$OS" in
        Linux*)
            echo "linux"
            ;;
        Darwin*)
            echo "macos"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            error "Windows is not supported. Please use WSL (Windows Subsystem for Linux)."
            error "Install WSL: https://docs.microsoft.com/en-us/windows/wsl/install"
            exit 1
            ;;
        *)
            error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
}

# Detect architecture
detect_arch() {
    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64|amd64)
            echo "x86_64"
            ;;
        arm64|aarch64)
            echo "aarch64"
            ;;
        *)
            error "Unsupported architecture: $ARCH"
            error "Supported architectures: x86_64 (amd64), arm64 (aarch64)"
            exit 1
            ;;
    esac
}

# Check for download tool (curl or wget)
detect_downloader() {
    if command -v curl >/dev/null 2>&1; then
        echo "curl"
    elif command -v wget >/dev/null 2>&1; then
        echo "wget"
    else
        error "Neither curl nor wget found. Please install one of them."
        exit 1
    fi
}

# Download a file
download() {
    URL="$1"
    OUTPUT="$2"
    DOWNLOADER="$3"

    case "$DOWNLOADER" in
        curl)
            curl -fsSL "$URL" -o "$OUTPUT"
            ;;
        wget)
            wget -q "$URL" -O "$OUTPUT"
            ;;
    esac
}

# Get the latest release version
get_latest_version() {
    DOWNLOADER="$1"

    case "$DOWNLOADER" in
        curl)
            VERSION=$(curl -fsSL "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
            ;;
        wget)
            VERSION=$(wget -qO- "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
            ;;
    esac

    if [ -z "$VERSION" ]; then
        # Fallback to latest download URL if API fails
        echo "latest"
    else
        echo "$VERSION"
    fi
}

# Determine install directory
determine_install_dir() {
    # Try user-local directory first
    if [ -d "$INSTALL_DIR_PRIMARY" ] && [ -w "$INSTALL_DIR_PRIMARY" ]; then
        echo "$INSTALL_DIR_PRIMARY"
        return
    fi

    # Create .local/bin if it doesn't exist but .local does
    if [ -d "$HOME/.local" ] && [ -w "$HOME/.local" ]; then
        mkdir -p "$INSTALL_DIR_PRIMARY"
        echo "$INSTALL_DIR_PRIMARY"
        return
    fi

    # Check if .local can be created
    if [ -w "$HOME" ]; then
        mkdir -p "$INSTALL_DIR_PRIMARY"
        echo "$INSTALL_DIR_PRIMARY"
        return
    fi

    # Fallback to /usr/local/bin
    if [ -d "$INSTALL_DIR_FALLBACK" ] && [ -w "$INSTALL_DIR_FALLBACK" ]; then
        echo "$INSTALL_DIR_FALLBACK"
        return
    fi

    # Need sudo for /usr/local/bin
    warn "Cannot write to $INSTALL_DIR_PRIMARY or $INSTALL_DIR_FALLBACK"
    warn "Will attempt to install to $INSTALL_DIR_FALLBACK with sudo"
    echo "$INSTALL_DIR_FALLBACK"
}

# Check if directory is in PATH
is_in_path() {
    DIR="$1"
    case ":$PATH:" in
        *":$DIR:"*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Print PATH instructions
print_path_instructions() {
    INSTALL_DIR="$1"

    echo ""
    warn "The installation directory is not in your PATH."
    echo ""
    echo "Add it to your PATH by adding this line to your shell configuration:"
    echo ""

    # Detect shell
    SHELL_NAME="$(basename "$SHELL")"
    case "$SHELL_NAME" in
        bash)
            echo "  ${BOLD}echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.bashrc${NC}"
            echo ""
            echo "Then reload your shell:"
            echo "  ${BOLD}source ~/.bashrc${NC}"
            ;;
        zsh)
            echo "  ${BOLD}echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.zshrc${NC}"
            echo ""
            echo "Then reload your shell:"
            echo "  ${BOLD}source ~/.zshrc${NC}"
            ;;
        fish)
            echo "  ${BOLD}fish_add_path $INSTALL_DIR${NC}"
            ;;
        *)
            echo "  ${BOLD}export PATH=\"$INSTALL_DIR:\$PATH\"${NC}"
            echo ""
            echo "Add this line to your shell's configuration file."
            ;;
    esac
    echo ""
}

# Main installation function
main() {
    echo ""
    printf "${BOLD}AI SDK CLI Installer${NC}\n"
    echo "========================="
    echo ""

    # Detect system
    info "Detecting system..."
    OS=$(detect_os)
    ARCH=$(detect_arch)
    DOWNLOADER=$(detect_downloader)

    success "Detected: $OS-$ARCH (using $DOWNLOADER)"

    # Get version
    info "Checking latest version..."
    VERSION=$(get_latest_version "$DOWNLOADER")
    success "Latest version: $VERSION"

    # Construct download URL
    ARCHIVE_NAME="${BINARY_NAME}-${OS}-${ARCH}.tar.gz"
    if [ "$VERSION" = "latest" ]; then
        DOWNLOAD_URL="https://github.com/$GITHUB_REPO/releases/latest/download/$ARCHIVE_NAME"
    else
        DOWNLOAD_URL="https://github.com/$GITHUB_REPO/releases/download/$VERSION/$ARCHIVE_NAME"
    fi

    # Create temp directory
    TEMP_DIR=$(mktemp -d)
    ARCHIVE_PATH="$TEMP_DIR/$ARCHIVE_NAME"

    # Download
    info "Downloading $ARCHIVE_NAME..."
    if ! download "$DOWNLOAD_URL" "$ARCHIVE_PATH" "$DOWNLOADER"; then
        error "Failed to download from $DOWNLOAD_URL"
        error "Please check your internet connection and try again."
        exit 1
    fi
    success "Download complete"

    # Verify download
    if [ ! -f "$ARCHIVE_PATH" ] || [ ! -s "$ARCHIVE_PATH" ]; then
        error "Downloaded file is missing or empty"
        exit 1
    fi

    # Extract
    info "Extracting archive..."
    if ! tar -xzf "$ARCHIVE_PATH" -C "$TEMP_DIR"; then
        error "Failed to extract archive"
        error "The downloaded file may be corrupted. Please try again."
        exit 1
    fi
    success "Extraction complete"

    # Find the binary
    BINARY_PATH="$TEMP_DIR/$BINARY_NAME"
    if [ ! -f "$BINARY_PATH" ]; then
        # Try looking in a subdirectory
        BINARY_PATH=$(find "$TEMP_DIR" -name "$BINARY_NAME" -type f | head -n 1)
    fi

    if [ ! -f "$BINARY_PATH" ]; then
        error "Binary not found in archive"
        exit 1
    fi

    # Make binary executable
    chmod +x "$BINARY_PATH"

    # Determine install location
    INSTALL_DIR=$(determine_install_dir)
    INSTALL_PATH="$INSTALL_DIR/$BINARY_NAME"

    # Install binary
    info "Installing to $INSTALL_PATH..."

    if [ -w "$INSTALL_DIR" ]; then
        mv "$BINARY_PATH" "$INSTALL_PATH"
    else
        # Need sudo
        warn "Elevated permissions required"
        sudo mv "$BINARY_PATH" "$INSTALL_PATH"
    fi

    if [ ! -f "$INSTALL_PATH" ]; then
        error "Installation failed"
        exit 1
    fi

    # Re-sign on macOS (file operations can invalidate linker-signed code signatures)
    if [ "$OS" = "macos" ] && command -v codesign >/dev/null 2>&1; then
        codesign --sign - --force "$INSTALL_PATH" 2>/dev/null || true
    fi

    success "Installation complete"

    # Verify installation
    echo ""
    info "Verifying installation..."

    if is_in_path "$INSTALL_DIR"; then
        # Directory is in PATH, try running the binary
        if "$INSTALL_PATH" --version >/dev/null 2>&1; then
            INSTALLED_VERSION=$("$INSTALL_PATH" --version 2>&1 | head -n 1)
            success "Verified: $INSTALLED_VERSION"
        else
            success "Binary installed successfully"
        fi
    else
        success "Binary installed to $INSTALL_PATH"
        print_path_instructions "$INSTALL_DIR"
    fi

    # Print success message
    echo ""
    printf "${GREEN}${BOLD}Successfully installed AI SDK CLI!${NC}\n"
    echo ""
    echo "Next steps:"
    echo "  1. Configure the CLI with your OpenMetadata instance:"
    echo "     ${BOLD}ai-sdk configure${NC}"
    echo ""
    echo "  2. List available agents:"
    echo "     ${BOLD}ai-sdk agents list${NC}"
    echo ""
    echo "  3. Invoke an agent:"
    echo "     ${BOLD}ai-sdk invoke <agent-name> \"your question\"${NC}"
    echo ""
    echo "Documentation: https://docs.open-metadata.org/cli"
    echo ""
}

# Run main function
main
