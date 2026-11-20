#!/bin/sh
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${HOME}/.local/bin"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
    echo "erro: a Nativa requer Python 3.10 ou superior" >&2
    exit 1
}
mkdir -p "$TARGET"
chmod +x "$ROOT/nativa"
ln -sf "$ROOT/nativa" "$TARGET/nativa"
echo "Nativa instalada em $TARGET/nativa"
case ":$PATH:" in
    *":$TARGET:"*) ;;
    *) echo "adicione $TARGET ao seu PATH para usar o comando 'nativa'" ;;
esac
if python3 -c 'import pygame' 2>/dev/null; then
    echo "pygame encontrado: a biblioteca NAgame está pronta"
else
    echo "opcional: para usar a NAgame, instale o pygame (pip install -r $ROOT/requirements.txt)"
fi
