#!/bin/bash
# Double-click to install Flow (opens Terminal and runs the installer).
cd "$(dirname "$0")" && bash ./install.sh
echo; read -n 1 -s -r -p "Done. Press any key to close this window."
