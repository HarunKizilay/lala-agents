#!/bin/bash
# DO'da LALA ve ZEKY repolarını GitHub'dan otomatik günceller.
# systemd timer tarafından çalıştırılır — her 3 dakikada bir.

LOG=/var/log/lala-autopull.log

check_and_pull() {
    local dir=$1
    local service=$2

    cd "$dir" || return

    git fetch origin main -q 2>/dev/null || return

    LOCAL=$(git rev-parse HEAD 2>/dev/null)
    REMOTE=$(git rev-parse origin/main 2>/dev/null)

    if [ "$LOCAL" != "$REMOTE" ]; then
        git pull origin main -q
        systemctl restart "$service"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $service güncellendi → $REMOTE" >> "$LOG"
    fi
}

check_and_pull /root/LALA lala-bot
check_and_pull /root/ZEKY zeky
