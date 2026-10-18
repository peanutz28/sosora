//
//  SOSora_AppApp.swift
//  SOSora App
//

import SwiftUI

@main
struct SOSora_AppApp: App {
    @State private var store: AppStore
    @State private var location: LocationProvider

    init() {
        SOSoraTheme.applyChrome()
        _store = State(initialValue: AppStore())
        _location = State(initialValue: LocationProvider())
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(store)
                .environment(location)
                .preferredColorScheme(.dark)
                .tint(SOSoraColor.teal)
        }
    }
}
