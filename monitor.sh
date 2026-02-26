#!/bin/bash

# [TIKTOK BOT PRO] Monitoring & Management Script
# Save this file as monitor.sh on your VPS

# Colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function show_menu() {
    clear
    echo -e "${CYAN}==========================================${NC}"
    echo -e "${GREEN}      TIKTOK BOT PRO - DOCKER MONITOR     ${NC}"
    echo -e "${CYAN}==========================================${NC}"
    echo -e "1) 📊 Lihat Status Container (PS)"
    echo -e "2) 📝 Lihat Semua Log (Real-time)"
    echo -e "3) 🤖 Lihat Log Telegram Bot"
    echo -e "4) 🎵 Lihat Log Music Dashboard"
    echo -e "5) 🏠 Lihat Log Main Dashboard"
    echo -e "6) 🔄 Restart Semua Layanan"
    echo -e "7) 🛑 Matikan Semua Layanan (Stop)"
    echo -e "8) 🧹 Bersihkan Image/Container Sampah (Prune)"
    echo -e "9) 📈 Monitor Pemakaian RAM/CPU (Stats)"
    echo -e "0) 🚪 Keluar"
    echo -e "${CYAN}==========================================${NC}"
    echo -n "Pilih opsi [0-9]: "
}

while true; do
    show_menu
    read -r choice
    
    case $choice in
        1)
            echo -e "\n${YELLOW}>> Menampilkan Status Container...${NC}"
            docker compose ps
            read -n 1 -s -r -p "Tekan tombol apa saja untuk kembali..."
            ;;
        2)
            echo -e "\n${YELLOW}>> Menampilkan Semua Log (Ctrl+C untuk berhenti)...${NC}"
            docker compose logs -f
            ;;
        3)
            echo -e "\n${YELLOW}>> Menampilkan Log Bot Telegram...${NC}"
            docker compose logs -f telegram-bot
            ;;
        4)
            echo -e "\n${YELLOW}>> Menampilkan Log Music Dashboard...${NC}"
            docker compose logs -f music-dashboard
            ;;
        5)
            echo -e "\n${YELLOW}>> Menampilkan Log Main Dashboard...${NC}"
            docker compose logs -f main-dashboard
            ;;
        6)
            echo -e "\n${YELLOW}>> Melakukan Restart Semua Layanan...${NC}"
            docker compose restart
            echo -e "${GREEN}Berhasil di-restart!${NC}"
            sleep 2
            ;;
        7)
            echo -e "\n${RED}>> Mematikan Semua Layanan...${NC}"
            docker compose stop
            echo -e "${YELLOW}Semua layanan dihentikan.${NC}"
            sleep 2
            ;;
        8)
            echo -e "\n${YELLOW}>> Membersihkan sisa-sisa Docker...${NC}"
            docker system prune -f
            docker image prune -f
            echo -e "${GREEN}Pembersihan selesai!${NC}"
            sleep 2
            ;;
        9)
            echo -e "\n${YELLOW}>> Menampilkan Statistik Resource (Ctrl+C untuk berhenti)...${NC}"
            docker stats
            ;;
        0)
            echo -e "\n${GREEN}Sampai jumpa! 👋${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Opsi tidak valid! Berikan angka antara 0-9.${NC}"
            sleep 1
            ;;
    esac
done
