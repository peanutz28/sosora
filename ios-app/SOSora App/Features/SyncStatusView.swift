//
//  SyncStatusView.swift
//  SOSora App
//

import SwiftUI

struct SyncStatusView: View {
    @Environment(AppStore.self) private var store
    @State private var draftURL = ""
    @State private var urlError: String?

    var body: some View {
        SOSoraScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack(spacing: 10) {
                                Circle()
                                    .fill(store.isOnline ? SOSoraColor.teal : SOSoraColor.amber)
                                    .frame(width: 12, height: 12)
                                    .accessibilityHidden(true)
                                Text(store.isOnline ? "Online" : "Offline")
                                    .font(.system(size: 34, weight: .heavy, design: .rounded))
                                    .foregroundStyle(SOSoraColor.text)
                            }
                            Text(store.isOnline
                                 ? "This phone has a network. The demo server still has to accept each upload."
                                 : "No network. Saved reports stay on this phone.")
                                .font(.body)
                                .foregroundStyle(SOSoraColor.text)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        Spacer(minLength: 8)
                        SimulationTag()
                    }

                    PanelCard {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("\(store.pendingCount)")
                                .font(.system(size: 40, weight: .heavy, design: .rounded))
                                .foregroundStyle(store.pendingCount == 0 ? SOSoraColor.teal : SOSoraColor.amber)
                            Text(store.pendingCount == 1 ? "Report waiting" : "Reports waiting")
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(SOSoraColor.text)
                            Text("SOS text can upload. Road text uploads only when the server has that road. Hazards, photos, and simulated records stay on this phone.")
                                .font(.subheadline)
                                .foregroundStyle(SOSoraColor.text.opacity(0.9))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    PanelCard {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Demo server")
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(SOSoraColor.muted)
                            Text(serverTitle)
                                .font(.title3.weight(.heavy))
                                .foregroundStyle(SOSoraColor.text)
                            Text(store.serverDetail)
                                .font(.subheadline)
                                .foregroundStyle(SOSoraColor.text)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Server address")
                        DarkField(placeholder: "http://192.168.68.80:8000", text: $draftURL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)
                        Text("Simulator: 127.0.0.1 on this Mac. A physical phone needs that Mac’s address on the same network.")
                            .font(.subheadline)
                            .foregroundStyle(SOSoraColor.text.opacity(0.9))
                        InlineError(text: urlError)
                        OutlineButton(title: "Save address", systemImage: "link") {
                            urlError = store.saveAPIBaseURL(draftURL)
                        }
                    }

                    TealButton(
                        title: store.isSyncing ? "Checking…" : "Sync now",
                        systemImage: "arrow.triangle.2.circlepath"
                    ) {
                        Task { await store.testConnection() }
                    }
                    .disabled(store.isSyncing)
                    .opacity(store.isSyncing ? 0.6 : 1)

                    if let persistenceError = store.persistenceError {
                        DisclaimerBanner(text: persistenceError)
                    }

                    OutlineButton(title: "Restore simulated records", systemImage: "arrow.counterclockwise") {
                        store.restoreSimulatedRecords()
                    }

                    SafetyNote(text: "Stored on this phone. Not sent by radio.")
                }
                .padding(20)
                .padding(.bottom, 28)
            }
            .contentMargins(.bottom, 48, for: .scrollContent)
        }
        .navigationTitle("Sync")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                RoleSwitchButton()
            }
        }
        .onAppear {
            draftURL = store.apiBaseURL
        }
    }

    private var serverTitle: String {
        switch store.serverReachable {
        case .some(true): "Reachable"
        case .some(false): "Not reachable"
        case nil: "Not checked"
        }
    }
}
