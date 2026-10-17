# Иконки AIX OS

В эту папку нужно положить 2 PNG-файла:

- `icon.png` — иконка приложения (1024×1024, квадратная)
- `icon_foreground.png` — иконка для adaptive (1024×1024, с прозрачностью по краям)
- `splash.png` — логотип на splash (512×512, прозрачный фон)

## Как сгенерировать

**Вариант A — из нашей SVG-иконки** (лежит в `web/landing/favicon.svg`):

Конвертируй SVG → PNG 1024×1024 через:
- Онлайн: https://cloudconvert.com/svg-to-png
- Или VSCode extension: "SVG to PNG"

**Вариант B — через наш скрипт (следующий батч)**  
Скрипт `scripts/make_mobile_icons.py` генерирует PNG напрямую из Pillow.

## После добавления

Запусти:
flutter pub run flutter_launcher_icons
flutter pub run flutter_native_splash:create

text

Они сами подставят иконки во все размеры Android.