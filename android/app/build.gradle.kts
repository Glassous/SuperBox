import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
}

val localEnv = Properties().apply {
    val envFile = rootProject.file(".env")
    if (envFile.isFile) envFile.inputStream().use(::load)
}
val configuredApiBaseUrl = (System.getenv("SUPERBOX_API_BASE_URL")
    ?.takeIf(String::isNotBlank)
    ?: localEnv.getProperty("SUPERBOX_API_BASE_URL").orEmpty())
    .trim().trimEnd('/')

fun quotedBuildConfig(value: String): String = "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""

android {
    namespace = "com.glassous.superbox"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.glassous.superbox"
        minSdk = 33
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    buildTypes {
        debug {
            val url = configuredApiBaseUrl.ifEmpty { "http://10.0.2.2:8087" }
            require(url.startsWith("https://") || url.startsWith("http://")) {
                "SUPERBOX_API_BASE_URL must be an HTTP(S) origin"
            }
            buildConfigField("String", "API_BASE_URL", quotedBuildConfig(url))
        }
        release {
            val url = configuredApiBaseUrl
            buildConfigField("String", "API_BASE_URL", quotedBuildConfig(url))
            optimization { enable = false }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

tasks.matching { it.name == "preReleaseBuild" }.configureEach {
    doFirst {
        require(configuredApiBaseUrl.startsWith("https://") && configuredApiBaseUrl.length > "https://".length) {
            "Release builds require an HTTPS SUPERBOX_API_BASE_URL in android/.env or the environment"
        }
    }
}

dependencies {
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.material3)
    implementation(libs.activity.compose)
    implementation(libs.navigation.compose)
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.coroutines.android)
    implementation(libs.androidx.core.ktx)

    debugImplementation(libs.compose.ui.tooling)
    debugImplementation(libs.compose.ui.test.manifest)
    testImplementation(libs.junit)
    testImplementation(libs.json.jvm)
    androidTestImplementation(platform(libs.compose.bom))
    androidTestImplementation(libs.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.junit)
}
