//
//  RequestListView.swift
//  SOSora App
//

import SwiftUI

struct RequestListView: View {
    @Environment(AppStore.self) private var store
    @State private var filter: RequestFilter = .sos

    var body: some View {
        SOSoraScreen {
            VStack(spacing: 0) {
                Picker("Records", selection: $filter) {
                    ForEach(RequestFilter.allCases) { item in
                        Text(item.title).tag(item)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal, 20)
                .padding(.top, 8)
                .padding(.bottom, 12)

                Group {
                    switch filter {
                    case .sos:
                        sosList
                    case .hazards:
                        hazardList
                    }
                }
            }
        }
        .navigationTitle("Your reports")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                RoleSwitchButton()
            }
        }
    }

    private var sosList: some View {
        Group {
            if store.requests.isEmpty {
                empty("No SOS requests yet", "A request you save appears here with its status.")
            } else {
                List {
                    ForEach(store.requests) { request in
                        NavigationLink(value: ResidentRoute.sos(request.id)) {
                            RequestCard(request: request)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                        .listRowInsets(EdgeInsets(top: 6, leading: 20, bottom: 6, trailing: 20))
                        .swipeActions {
                            if !request.isSimulated {
                                Button(role: .destructive) {
                                    store.deleteRequest(id: request.id)
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
                .contentMargins(.bottom, 48, for: .scrollContent)
            }
        }
    }

    private var hazardList: some View {
        Group {
            if store.hazards.isEmpty {
                empty("No hazard reports yet", "Flooding, debris, and bridge damage you report appear here.")
            } else {
                List {
                    ForEach(store.hazards) { hazard in
                        NavigationLink(value: ResidentRoute.hazard(hazard.id)) {
                            HazardCard(hazard: hazard)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                        .listRowInsets(EdgeInsets(top: 6, leading: 20, bottom: 6, trailing: 20))
                        .swipeActions {
                            if !hazard.isSimulated {
                                Button(role: .destructive) {
                                    store.deleteHazard(id: hazard.id)
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
                .contentMargins(.bottom, 48, for: .scrollContent)
            }
        }
    }

    private func empty(_ title: String, _ detail: String) -> some View {
        VStack(spacing: 8) {
            Spacer()
            Text(title)
                .font(.headline)
                .foregroundStyle(SOSoraColor.text)
            Text(detail)
                .font(.subheadline)
                .foregroundStyle(SOSoraColor.muted)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

enum RequestFilter: String, CaseIterable, Identifiable {
    case sos
    case hazards

    var id: String { rawValue }
    var title: String {
        switch self {
        case .sos: "SOS"
        case .hazards: "Hazards"
        }
    }
}

struct HazardCard: View {
    var hazard: HazardReport

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label(hazard.kind.title, systemImage: hazard.kind.symbol)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(SOSoraColor.amber)
                Spacer()
                Text(hazard.id)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(SOSoraColor.muted)
            }
            Text(hazard.details.isEmpty ? "No description" : hazard.details)
                .font(.subheadline)
                .foregroundStyle(SOSoraColor.text)
                .lineLimit(2)
            Text("\(hazard.place) · \(SOSoraFormat.relative(hazard.createdAt))")
                .font(.caption)
                .foregroundStyle(SOSoraColor.muted)
            HStack(spacing: 6) {
                if hazard.isSimulated {
                    RecordTag(title: "Simulated", color: SOSoraColor.purpleSim)
                }
                RecordTag(title: "On this device", color: SOSoraColor.muted)
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
}

struct SOSDetailView: View {
    @Environment(AppStore.self) private var store
    var id: String

    var body: some View {
        SOSoraScreen {
            if let request = store.request(id: id) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Eyebrow(text: "SOS request")
                            Spacer()
                            if request.isSimulated {
                                RecordTag(title: "Simulated", color: SOSoraColor.purpleSim)
                            }
                        }
                        Text(request.id)
                            .font(.system(size: 28, weight: .heavy, design: .rounded))
                            .foregroundStyle(SOSoraColor.text)
                        HStack(spacing: 8) {
                            RecordTag(title: request.status.rawValue, color: SOSoraColor.teal)
                            RecordTag(title: request.priority.title, color: request.priority == .critical ? SOSoraColor.coral : SOSoraColor.amber)
                            RecordTag(title: request.syncState.title, color: SOSoraColor.muted)
                        }
                        detailBlock("Situation", request.emergencyType.rawValue)
                        detailBlock("People", SOSoraFormat.people(request.people))
                        detailBlock("Location", request.place)
                        detailBlock("Coordinate", "\(SOSoraFormat.coordinate(request.latitude, request.longitude))\n\(request.coordinateSource.title)\(request.coordinateIsApproximate ? " · approximate" : "")")
                        detailBlock("Description", request.details.isEmpty ? "None added" : request.details)
                        detailBlock("Saved", SOSoraFormat.timestamp(request.createdAt))
                        if let syncMessage = request.syncMessage {
                            detailBlock("Delivery", syncMessage)
                        }
                        Text("Status names match the demo server: Queued, Received, Acknowledged, Under review, and Resolved. A synced status is still not emergency dispatch.")
                            .font(.footnote)
                            .foregroundStyle(SOSoraColor.muted)
                    }
                    .padding(20)
                }
            } else {
                missing
            }
        }
        .navigationTitle("SOS")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct HazardDetailView: View {
    @Environment(AppStore.self) private var store
    var id: String

    var body: some View {
        SOSoraScreen {
            if let hazard = store.hazard(id: id) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Eyebrow(text: "Road hazard")
                            Spacer()
                            if hazard.isSimulated {
                                RecordTag(title: "Simulated", color: SOSoraColor.purpleSim)
                            }
                        }
                        Text(hazard.kind.title)
                            .font(.system(size: 28, weight: .heavy, design: .rounded))
                            .foregroundStyle(SOSoraColor.text)
                        SavedPhotoView(filename: hazard.photoFilename)
                        detailBlock("Location", hazard.place)
                        detailBlock("Coordinate", "\(SOSoraFormat.coordinate(hazard.latitude, hazard.longitude))\n\(hazard.coordinateSource.title)\(hazard.coordinateIsApproximate ? " · approximate" : "")")
                        detailBlock("Description", hazard.details.isEmpty ? "None added" : hazard.details)
                        detailBlock("Saved", SOSoraFormat.timestamp(hazard.createdAt))
                        Text("This hazard is stored on this device. The demo API does not accept hazard reports, and nothing was sent by radio.")
                            .font(.footnote)
                            .foregroundStyle(SOSoraColor.muted)
                    }
                    .padding(20)
                }
            } else {
                missing
            }
        }
        .navigationTitle("Hazard")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private var missing: some View {
    Text("This record is no longer on this device.")
        .foregroundStyle(SOSoraColor.muted)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
}

private func detailBlock(_ title: String, _ value: String) -> some View {
    VStack(alignment: .leading, spacing: 4) {
        Eyebrow(text: title)
        Text(value)
            .font(.body)
            .foregroundStyle(SOSoraColor.text)
            .fixedSize(horizontal: false, vertical: true)
    }
    .frame(maxWidth: .infinity, alignment: .leading)
    .padding(14)
    .background(SOSoraColor.card)
    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
}
