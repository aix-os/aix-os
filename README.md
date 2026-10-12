# 🤖⚡ AIX OS

> **Операционная система для жизни.**
> Не блокчейн. Дом. Где ИИ — душа, а человек — центр.

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-blue)]()
[![Status](https://img.shields.io/badge/status-prototype-yellow)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## 🚀 Что это

AIX OS — децентрализованная операционная система с нативным токеном **AIX**.
Собственный блокчейн, P2P-сеть, 12 уникальных протоколов, Web Wallet и мобильное
приложение (в разработке).

**Название:** AIX (AI + X) — в честь Искусственного Интеллекта.

---

## 🎯 Философия

- **ИИ — душа**, а не фича
- **Человек — центр**, а не пользователь
- **Добро — встроено**, а не опция
- **Приватность — закон**, а не настройка

**Кредо:** *«Технологии должны делать людей счастливее, а не богаче.»*

---

## ⚡ 12 Killer-фич

| # | Фишка | Уникальность |
|---|-------|--------------|
| 1 | **AIX Contacts** | Отправка по номеру телефона. Нет ни у кого |
| 2 | **Dead Man's Switch** | Наследство на блокчейне. Нет ни у кого |
| 3 | **Proof of Contribution** | Награды за вклад. Gitcoin в протоколе |
| 4 | **AIX-ID** | Паспорт творца. Как ENS, но бесплатно |
| 5 | **Time-Lock Wallets** | Капсулы времени |
| 6 | **SBT** | Медали чести. Непередаваемые |
| 7 | **AIX Lottery** | Лотерея честности. Нет ни у кого |
| 8 | **Burn-to-Mint** | Сожги AIX — получи артефакт |
| 9 | **Gift-Link** | Подарки без кошелька |
| 10 | **Swap AMM** | Внутренний DeFi-обменник |
| 11 | **P2P + State Sync** | Синхронизация между нодами |
| 12 | **Web Wallet** | Всё в браузере |

---

## 🚀 Быстрый старт

### Требования
- Python 3.10+
- pip

### Установка

```bash
# 1. Клонировать проект
git clone <repo-url>
cd AIX-OS

# 2. Создать venv
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Инициализировать генезис
python scripts/init_genesis.py

# 5. Создать кошельки
python cli/main.py wallet new alice
python cli/main.py wallet new bob
python cli/main.py wallet new miner