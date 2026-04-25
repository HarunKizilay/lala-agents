#!/bin/bash
# DO sunucusuna NVIDIA_API_KEY ekler ve servisi yeniden başlatır
# Kullanım: bash scripts/deploy_nvidia_key.sh nvapi-XXXXXXXX
#
# Çalıştırmadan önce: ssh root@165.245.213.201

DO_IP="165.245.213.201"
NVIDIA_KEY="$1"

if [ -z "$NVIDIA_KEY" ]; then
    echo "Kullanım: bash scripts/deploy_nvidia_key.sh nvapi-SIZIN_KEYINIZ"
    exit 1
fi

echo "DO sunucusuna bağlanılıyor ($DO_IP)..."

ssh root@$DO_IP bash <<EOF
# .env dosyasına NVIDIA_API_KEY ekle (varsa güncelle, yoksa ekle)
ENV_FILE="/root/LALA/.env"

if grep -q "NVIDIA_API_KEY" "\$ENV_FILE" 2>/dev/null; then
    sed -i "s|NVIDIA_API_KEY=.*|NVIDIA_API_KEY=$NVIDIA_KEY|" "\$ENV_FILE"
    echo "✅ NVIDIA_API_KEY güncellendi"
else
    echo "" >> "\$ENV_FILE"
    echo "# NVIDIA NIM" >> "\$ENV_FILE"
    echo "NVIDIA_API_KEY=$NVIDIA_KEY" >> "\$ENV_FILE"
    echo "NVIDIA_MODEL=deepseek-ai/deepseek-v4-flash" >> "\$ENV_FILE"
    echo "✅ NVIDIA_API_KEY eklendi"
fi

# Servisi yeniden başlat
systemctl restart lala-bot.service
sleep 3
systemctl status lala-bot.service --no-pager | tail -5
echo "✅ lala-bot servisi yeniden başlatıldı"
EOF
