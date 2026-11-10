plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "vn.navitaxi.navi_taxi_test"
    compileSdk = 36
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    defaultConfig {
        applicationId = "vn.navitaxi.navi_taxi_test"
        minSdk = 24
        targetSdk = 35
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
    }
}

flutter {
    source = "../.."
}

/** All release APK/AAB packaging must run the independent P0 gate. */
val verifySovereigntyP0 by tasks.registering(Exec::class) {
    val repositoryRoot = rootProject.projectDir.parentFile
    workingDir(repositoryRoot)
    commandLine(
        "python3",
        "pipeline/vietnam_sovereignty_validator.py",
        "--repo-root",
        repositoryRoot.absolutePath,
        "--mode",
        "release"
    )
}

tasks.matching {
    it.name in setOf(
        "assembleRelease",
        "bundleRelease",
        "packageRelease",
        "packageReleaseBundle"
    )
}.configureEach {
    dependsOn(verifySovereigntyP0)
}
