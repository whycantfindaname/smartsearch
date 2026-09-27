// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SmartSearchDesktop",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "SmartSearchDesktop", targets: ["SmartSearchDesktop"]),
    ],
    targets: [
        .executableTarget(name: "SmartSearchDesktop", resources: [.copy("Localization.json")]),
        .testTarget(name: "SmartSearchDesktopTests", dependencies: ["SmartSearchDesktop"]),
    ]
)
