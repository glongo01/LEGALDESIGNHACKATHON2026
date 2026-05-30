#!/bin/bash
# Convert LEXIA Chrome MV3 extension to Safari Web Extension (requires Xcode + macOS)
# Run from the LEXIA-Hackathon/ root directory.

set -e

echo "Converting extension/ to Safari Web Extension..."
xcrun safari-web-extension-converter extension/ \
    --project-location . \
    --app-name "LEXIA" \
    --bundle-identifier "eu.lexia.rights-checker" \
    --swift

echo ""
echo "Done! Open LEXIA/LEXIA.xcodeproj in Xcode, then:"
echo "  1. Select your development team (Signing & Capabilities)"
echo "  2. Build & Run the Mac app (⌘R)"
echo "  3. Enable in Safari → Settings → Extensions → LEXIA"
echo "  4. Allow access to localhost and the sites you want to check"
