//
//  ResidentHomeView.swift
//  SOSora App
//

import SwiftUI

struct ResidentShell: View {
    var body: some View {
        TabView {
            NavigationStack {
                ResidentHomeView()
                    .residentDestinations()
            }
            .tabItem { Label("Home", systemImage: "house.fill") }

            NavigationStack {
                RequestListView()
                    .residentDestinations()
            }
            .tabItem { Label("Requests", systemImage: "list.bullet.rectangle") }

            NavigationStack {
                SyncStatusView()
            }
            .tabItem { Label("Sync", systemImage: "arrow.triangle.2.circlepath") }
        }
        .tint(SOSoraColor.teal)
    }
}

struct ResidentHomeView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        SOSoraScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    SafetyNote(text: "Saved on this phone. This is not an emergency call.")

                    NavigationLink(value: ResidentRoute.sosForm) {
                        primaryAction(
                            title: "Request Help",
                            symbol: "sos",
                            colors: [
                                Color(red: 1.0, green: 0.45, blue: 0.52),
                                Color(red: 0.82, green: 0.22, blue: 0.34)
                            ],
                            foreground: .white,
                            shadow: SOSoraColor.coral.opacity(0.28)
                        )
                    }
                    .buttonStyle(.plain)
                    .accessibilityHint("Opens the SOS request form")

                    NavigationLink(value: ResidentRoute.roadMap) {
                        primaryAction(
                            title: "Report Roads",
                            symbol: "map.fill",
                            colors: [
                                Color(red: 0.45, green: 0.90, blue: 0.84),
                                Color(red: 0.18, green: 0.62, blue: 0.58)
                            ],
                            foreground: SOSoraColor.tealInk,
                            shadow: SOSoraColor.teal.opacity(0.22)
                        )
                    }
                    .buttonStyle(.plain)
                    .accessibilityHint("Opens the road map")

                    if let latest = store.requests.first {
                        VStack(alignment: .leading, spacing: 10) {
                            Eyebrow(text: "Latest request")
                            NavigationLink(value: ResidentRoute.sos(latest.id)) {
                                RequestCard(request: latest)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(20)
                .padding(.bottom, 24)
            }
            .contentMargins(.bottom, 48, for: .scrollContent)
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                RoleSwitchButton()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Eyebrow(text: "Resident")
                Spacer()
                SimulationTag()
            }
            Text("Are you safe?")
                .font(.system(size: 34, weight: .heavy, design: .rounded))
                .foregroundStyle(SOSoraColor.text)
        }
    }

    private func primaryAction(
        title: String,
        symbol: String,
        colors: [Color],
        foreground: Color,
        shadow: Color
    ) -> some View {
        VStack(spacing: 10) {
            Image(systemName: symbol)
                .font(.system(size: 32, weight: .bold))
            Text(title)
                .font(.system(size: 28, weight: .heavy, design: .rounded))
        }
        .foregroundStyle(foreground)
        .frame(maxWidth: .infinity)
        .padding(.vertical, 26)
        .background(
            LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing)
        )
        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
        .shadow(color: shadow, radius: 16, y: 8)
    }
}

struct RequestCard: View {
    var request: SOSRequest

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                HStack(spacing: 6) {
                    Circle()
                        .fill(request.priority == .critical ? SOSoraColor.coral : SOSoraColor.amber)
                        .frame(width: 8, height: 8)
                    Text(request.id)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(SOSoraColor.text)
                }
                Spacer()
                Text(request.priority.title.uppercased())
                    .font(.caption2.weight(.bold))
                    .tracking(0.6)
                    .foregroundStyle(SOSoraColor.muted)
            }
            Text(request.summary)
                .font(.subheadline)
                .foregroundStyle(SOSoraColor.text)
                .lineLimit(2)
            HStack {
                Text("\(request.place) · \(SOSoraFormat.people(request.people))")
                    .lineLimit(1)
                Spacer()
                Text(request.status.rawValue)
            }
            .font(.caption)
            .foregroundStyle(SOSoraColor.muted)
            HStack(spacing: 6) {
                if request.isSimulated {
                    RecordTag(title: "Simulated", color: SOSoraColor.purpleSim)
                }
                RecordTag(title: request.syncState.title, color: syncColor)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(SOSoraColor.card)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(SOSoraColor.line, lineWidth: 1)
        )
    }

    private var syncColor: Color {
        switch request.syncState {
        case .synced: SOSoraColor.teal
        case .failed: SOSoraColor.coral
        case .pending: SOSoraColor.amber
        case .localOnly: SOSoraColor.muted
        }
    }
}
