#!/bin/bash
mkdir -p /home/dehnert/github/cad-hub/apps/ifc/chat
cp /home/dehnert/github/platform/packages/cad-services/contrib/cad_toolkit.py /home/dehnert/github/cad-hub/apps/ifc/chat/toolkit.py
touch /home/dehnert/github/cad-hub/apps/ifc/chat/__init__.py
# Remove the docstring line about "Copy this file"
sed -i '/^Copy this file/d' /home/dehnert/github/cad-hub/apps/ifc/chat/toolkit.py
echo "CADToolkit copied to cad-hub"
