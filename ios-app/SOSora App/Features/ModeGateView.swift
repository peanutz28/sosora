//
//  ModeGateView.swift
//  SOSora App
//

import SwiftUI

struct ModeGateView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        SOSoraScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HStack {
                        BrandLockup()
                        Spacer()
                        SimulationTag()
                    }
                    .padding(.top, 12)

                    Text("Choose how you are using this demonstration.")
                        .font(.system(size: 28, weight: .heavy, design: .rounded))
                        .foregroundStyle(SOSoraColor.text)
                        .fixedSize(horizontal: false, vertical: true)

                    DisclaimerBanner(text: "Simulation only. Does not contact 911, dispatch help, verify a road, or transmit by radio.")

                    roleCard(
                        eyebrow: "RESIDENT",
                        title: "Request help",
                        detail: "Save an SOS, report a road hazard, and check the status of what you submitted.",
                        symbol: "sos",
                        tint: SOSoraColor.coral
                    ) {
                        store.chooseMode(.resident)
                    }

                    roleCard(
                        eyebrow: "FIELD RESPONDER",
                        title: "Report roads",
                        detail: "Mark a demonstration road passable, blocked, or unknown, with a photo, note, time, and coordinate.",
                        symbol: "map.fill",
                        tint: SOSoraColor.teal
                    ) {
                        store.chooseMode(.responder)
                    }
                }
                .padding(20)
            }
        }
    }

    private func roleCard(
        eyebrow: String,
        title: String,
        detail: String,
        symbol: String,
        tint: Color,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Image(systemName: symbol)
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(tint == SOSoraColor.coral ? .white : SOSoraColor.tealInk)
                        .frame(width: 48, height: 48)
                        .background(tint)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    Spacer()
                    Image(systemName: "arrow.right")
                        .font(.headline.weight(.bold))
                        .foregroundStyle(SOSoraColor.muted)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Eyebrow(text: eyebrow)
                    Text(title)
                        .font(.system(size: 24, weight: .heavy, design: .rounded))
                        .foregroundStyle(SOSoraColor.text)
                    Text(detail)
                        .font(.subheadline)
                        .foregroundStyle(SOSoraColor.muted)
                        .multilineTextAlignment(.leading)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(SOSoraColor.card)
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(SOSoraColor.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}
