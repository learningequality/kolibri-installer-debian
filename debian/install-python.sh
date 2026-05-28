#!/bin/bash
#
# Installs a bundled python-build-standalone Python to /opt/kolibri/python/
# if the system Python is below the required minimum version.
#
# Called from postinst. Expects bundled tarballs in /opt/kolibri/bundled/.
# Detects host architecture and extracts the matching tarball.

set -eo pipefail

INSTALL_DIR="/opt/kolibri/python"
BUNDLED_DIR="/opt/kolibri/bundled"
CONF_FILE="${BUNDLED_DIR}/python_versions.env"

if [ ! -f "$CONF_FILE" ]; then
    echo "install-python.sh: No python_versions.env found, skipping Python install." >&2
    exit 0
fi

source "$CONF_FILE"

# Check if system Python meets the minimum version requirement
check_system_python() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import sys
if sys.version_info >= ($PYTHON_MIN_MAJOR, $PYTHON_MIN_MINOR):
    sys.exit(0)
else:
    sys.exit(1)
" 2>/dev/null
        return $?
    fi
    return 1
}

if check_system_python; then
    echo "install-python.sh: System Python meets minimum version requirement (>= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}), skipping install."
    exit 0
fi

# Detect host architecture
DPKG_ARCH=$(dpkg --print-architecture 2>/dev/null || true)
case "$DPKG_ARCH" in
    amd64)
        ARCH="x86_64"
        EXPECTED_SHA256="$PYTHON_SHA256_X86_64"
        ;;
    arm64)
        ARCH="aarch64"
        EXPECTED_SHA256="$PYTHON_SHA256_AARCH64"
        ;;
    *)
        echo "install-python.sh: No bundled Python available for architecture: $DPKG_ARCH (only amd64 and arm64 are supported)" >&2
        echo "install-python.sh: Falling back to system Python." >&2
        exit 0
        ;;
esac

TARBALL="${BUNDLED_DIR}/cpython-${PYTHON_BUILD_STANDALONE_VERSION}-${ARCH}-unknown-linux-gnu-install_only_stripped.tar.gz"

if [ ! -f "$TARBALL" ]; then
    echo "install-python.sh: Bundled Python tarball not found: $TARBALL" >&2
    exit 1
fi

# Verify checksum
ACTUAL_SHA256=$(sha256sum "$TARBALL" | cut -d' ' -f1)
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "install-python.sh: SHA256 mismatch for $TARBALL" >&2
    echo "  Expected: $EXPECTED_SHA256" >&2
    echo "  Got:      $ACTUAL_SHA256" >&2
    exit 1
fi

# Extract Python to the install directory
echo "install-python.sh: Installing Python ${PYTHON_VERSION} (${ARCH}) to ${INSTALL_DIR}..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
tar -xzf "$TARBALL" -C "$INSTALL_DIR" --strip-components=1

echo "install-python.sh: Python ${PYTHON_VERSION} installed successfully."
