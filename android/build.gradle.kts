buildscript {
    dependencies {
        // AGP 9 has built-in Kotlin. Keep its compiler version aligned with Compose.
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.10")
    }
}

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.compose.compiler) apply false
}
