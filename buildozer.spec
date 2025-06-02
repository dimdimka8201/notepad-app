
[app]
title = Notepad
package.name = notepad
package.domain = org.my
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
source.include_patterns = icon.png
icon.filename = icon.png
requirements = python3,kivy==2.3.0,openssl
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25.2.9519653
android.sdk_path = ~/.buildozer/android/platform/android-sdk
android.ndk_path = ~/.buildozer/android/platform/android-sdk/ndk/25.2.9519653
android.archs = arm64-v8a
log_level = 2
android.gradle_version = 8.1
android.gradle_plugin_version = 8.1.0
android.ant_path = /usr/bin
android.skip_update = True
p4a.branch = master
