//
//  LocationEditor.swift
//  SOSora App
//

import SwiftUI
import CoreLocation

struct LocationEditor: View {
    @Binding var place: String
    @Binding var latitude: Double
    @Binding var longitude: Double
    @Binding var source: CoordinateSource
    @Binding var approximate: Bool

    @Environment(LocationProvider.self) private var location
    @State private var waitingForFix = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            FieldLabel(text: "Location")
            DarkField(placeholder: "Street, neighborhood, or landmark", text: $place)
                .onChange(of: place) { _, _ in
                    if source == .gps {
                        source = approximate ? .approximateArea : .gps
                    }
                }
            Button {
                waitingForFix = true
                location.request()
                if let latest = location.latest {
                    apply(latest)
                }
            } label: {
                Label(waitingForFix && location.latest == nil ? "Looking for GPS…" : "Use current GPS", systemImage: "location.fill")
                    .font(.subheadline.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .foregroundStyle(SOSoraColor.teal)
                    .background(SOSoraColor.teal.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .stroke(SOSoraColor.teal.opacity(0.45), lineWidth: 1)
                    )
            }
            .buttonStyle(.plain)

            Text(coordinateCaption)
                .font(.footnote)
                .foregroundStyle(approximate ? SOSoraColor.amber : SOSoraColor.muted)
                .fixedSize(horizontal: false, vertical: true)

            if let message = location.message {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(SOSoraColor.amber)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .onChange(of: location.latest) { _, latest in
            guard waitingForFix, let latest else { return }
            apply(latest)
        }
    }

    private var coordinateCaption: String {
        if approximate {
            return "No GPS fix yet. This will save the Swannanoa demonstration coordinate and mark it approximate."
        }
        return "\(source.title) · \(SOSoraFormat.coordinate(latitude, longitude))"
    }

    private func apply(_ fix: CLLocation) {
        latitude = fix.coordinate.latitude
        longitude = fix.coordinate.longitude
        source = .gps
        approximate = false
        waitingForFix = false
        Task {
            let typed = place.trimmingCharacters(in: .whitespacesAndNewlines)
            guard typed.isEmpty, let name = await location.placeName(for: fix) else { return }
            place = name
        }
    }
}

struct RoleSwitchButton: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        Button("Switch role", action: store.leaveMode)
            .font(.subheadline.weight(.semibold))
    }
}

extension View {
    func residentDestinations() -> some View {
        navigationDestination(for: ResidentRoute.self) { route in
            switch route {
            case .sosForm:
                SOSFormView()
            case .roadMap:
                ResponderMapView(showsBackButton: true)
                    .toolbar(.hidden, for: .navigationBar)
            case .hazardForm:
                HazardFormView()
            case .sos(let id):
                SOSDetailView(id: id)
            case .hazard(let id):
                HazardDetailView(id: id)
            }
        }
    }
}
