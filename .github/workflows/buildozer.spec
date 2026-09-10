[app]
title = Перегрузка: Последний Протокол
package.name = cyberrogue
package.domain = org.cyberrogue
source.dir = .
source.include_exts = py,png,jpg,jpeg,json,ttf,otf
version = 1.0.0
requirements = python3,pygame-ce
orientation = portrait
fullscreen = 1
android.permissions = INTERNET, VIBRATE
android.api = 30
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True
android.log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
