"""
AIX OS — подготовка Android-сборки.

Патчит:
  android/app/build.gradle.kts — minSdk=23, targetSdk=34, version
  android/app/src/main/res/values/styles.xml — тема тёмная

Создаёт:
  flutter_launcher_icons.yaml — иконки приложения
  flutter_native_splash.yaml — splash screen

Идемпотентен. Бэкапы: *.android.bak

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_android_build.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLUTTER = ROOT / "mobile" / "flutter_app"

BUILD_GRADLE = FLUTTER / "android" / "app" / "build.gradle.kts"
STYLES_XML = FLUTTER / "android" / "app" / "src" / "main" / "res" / "values" / "styles.xml"
ICONS_YAML = FLUTTER / "flutter_launcher_icons.yaml"
SPLASH_YAML = FLUTTER / "flutter_native_splash.yaml"


def patch_build_gradle() -> None:
    print(f"\n[build.gradle.kts]")
    if not BUILD_GRADLE.exists():
        print(f"  [WARN] не найден: {BUILD_GRADLE}")
        return

    src = BUILD_GRADLE.read_text(encoding="utf-8")
    original = src

    # minSdk
    src = re.sub(
        r"minSdk\s*=\s*(flutter\.minSdkVersion|\d+)",
        "minSdk = 23",
        src,
    )
    # targetSdk
    src = re.sub(
        r"targetSdk\s*=\s*(flutter\.targetSdkVersion|\d+)",
        "targetSdk = 34",
        src,
    )
    # compileSdk
    src = re.sub(
        r"compileSdk\s*=\s*(flutter\.compileSdkVersion|\d+)",
        "compileSdk = 34",
        src,
    )
    # applicationId — оставим как есть, но проверим
    if "applicationId" in src and "com.example" in src:
        src = re.sub(
            r'applicationId\s*=\s*"com\.example\.[^"]+"',
            'applicationId = "os.aix.wallet"',
            src,
        )
        print("  applicationId изменён на os.aix.wallet")

    if src == original:
        print("  ничего не изменилось (или уже настроено)")
        return

    bak = BUILD_GRADLE.with_suffix(".kts.android.bak")
    bak.write_bytes(BUILD_GRADLE.read_bytes())
    print(f"  backup -> {bak.name}")

    BUILD_GRADLE.write_text(src, encoding="utf-8")
    print("  OK: minSdk=23, targetSdk=34, compileSdk=34")


def patch_styles() -> None:
    print(f"\n[styles.xml]")
    if not STYLES_XML.exists():
        print(f"  [WARN] не найден: {STYLES_XML}")
        return

    src = STYLES_XML.read_text(encoding="utf-8")

    # Проверяем что тема тёмная
    if "Theme.Black.NoTitleBar" in src and "windowBackground" in src:
        print("  уже настроено")
        return

    bak = STYLES_XML.with_suffix(".xml.android.bak")
    bak.write_bytes(STYLES_XML.read_bytes())

    new_content = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <!-- Тёмная тема AIX OS: космос -->

    <style name="LaunchTheme" parent="@android:style/Theme.Black.NoTitleBar">
        <item name="android:windowBackground">@drawable/launch_background</item>
    </style>

    <style name="NormalTheme" parent="@android:style/Theme.Black.NoTitleBar">
        <item name="android:windowBackground">@android:color/black</item>
        <item name="android:statusBarColor">#0A0E27</item>
        <item name="android:navigationBarColor">#0A0E27</item>
        <item name="android:windowLightStatusBar">false</item>
    </style>
</resources>
'''
    STYLES_XML.write_text(new_content, encoding="utf-8")
    print(f"  backup -> {bak.name}")
    print("  OK: тёмная тема (космос)")


def create_icons_yaml() -> None:
    print(f"\n[flutter_launcher_icons.yaml]")
    if ICONS_YAML.exists():
        print("  уже существует")
        return

    content = '''# AIX OS — генерация иконок приложения
# Запуск: flutter pub run flutter_launcher_icons

flutter_launcher_icons:
  android: "ic_launcher"
  ios: false
  image_path: "assets/icon/icon.png"
  min_sdk_android: 23
  adaptive_icon_background: "#0A0E27"
  adaptive_icon_foreground: "assets/icon/icon_foreground.png"
  remove_alpha_ios: true
'''
    ICONS_YAML.write_text(content, encoding="utf-8")
    print("  создан")


def create_splash_yaml() -> None:
    print(f"\n[flutter_native_splash.yaml]")
    if SPLASH_YAML.exists():
        print("  уже существует")
        return

    content = '''# AIX OS — splash screen
# Запуск: flutter pub run flutter_native_splash:create

flutter_native_splash:
  color: "#0A0E27"
  image: "assets/icon/splash.png"
  android: true
  ios: false
  web: false
  android_12:
    image: "assets/icon/splash.png"
    color: "#0A0E27"
    icon_background_color: "#0A0E27"
'''
    SPLASH_YAML.write_text(content, encoding="utf-8")
    print("  создан")


def main() -> int:
    if not FLUTTER.exists():
        print(f"[FATAL] {FLUTTER} не найден")
        return 1

    print("AIX OS — Android build подготовка")

    patch_build_gradle()
    patch_styles()
    create_icons_yaml()
    create_splash_yaml()

    print()
    print("OK. Дальше:")
    print("  1) Скопируй PNG-иконки в assets/icon/")
    print("  2) Запусти: flutter pub add dev:flutter_launcher_icons")
    print("              flutter pub add dev:flutter_native_splash")
    print("              flutter pub get")
    print("              flutter pub run flutter_launcher_icons")
    print("              flutter pub run flutter_native_splash:create")
    return 0


if __name__ == "__main__":
    sys.exit(main())