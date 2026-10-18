//
//  ContentView.swift
//  SOSora App
//

import SwiftUI

struct ContentView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        Group {
            switch store.mode {
            case .resident:
                ResidentShell()
            case .responder:
                ResponderShell()
            case nil:
                ModeGateView()
            }
        }
        .background(SOSoraColor.background.ignoresSafeArea())
        .overlay(alignment: .bottom) {
            if let toast = store.toast {
                ToastBanner(text: toast)
                    .padding(.bottom, 24)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.2), value: store.toast)
    }
}

#Preview {
    ContentView()
        .environment(AppStore(preview: true))
        .environment(LocationProvider())
        .preferredColorScheme(.dark)
}
