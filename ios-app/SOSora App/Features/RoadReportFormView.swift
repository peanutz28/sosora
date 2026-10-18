//
//  RoadReportFormView.swift
//  SOSora App
//

import SwiftUI
import CoreLocation

struct RoadReportFormView: View {
    @Environment(AppStore.self) private var store
    @Environment(LocationProvider.self) private var location
    @Environment(\.dismiss) private var dismiss

    var segment: RoadSegment

    @State private var condition: RoadCondition = .blocked
    @State private var details = ""
    @State private var latitude: Double
    @State private var longitude: Double
    @State private var source: CoordinateSource = .road
    @State private var observedAt = Date.now
    @State private var photoData: Data?
    @FocusState private var focused: Bool

    init(segment: RoadSegment) {
        self.segment = segment
        let point = segment.midpoint
        _latitude = State(initialValue: point.latitude)
        _longitude = State(initialValue: point.longitude)
    }

    var body: some View {
        SOSoraScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 4) {
                        Eyebrow(text: "Road")
                        Text(segment.name)
                            .font(.system(size: 24, weight: .heavy, design: .rounded))
                            .foregroundStyle(SOSoraColor.text)
                        Text("Demonstration geometry, not a validated street network.")
                            .font(.footnote)
                            .foregroundStyle(SOSoraColor.muted)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Observed condition")
                        ForEach(RoadCondition.allCases) { item in
                            Button {
                                condition = item
                            } label: {
                                HStack(spacing: 12) {
                                    Image(systemName: item.symbol)
                                        .foregroundStyle(color(for: item))
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(item.title)
                                            .font(.headline)
                                            .foregroundStyle(SOSoraColor.text)
                                        Text(item.detail)
                                            .font(.caption)
                                            .foregroundStyle(SOSoraColor.muted)
                                    }
                                    Spacer()
                                    if condition == item {
                                        Image(systemName: "checkmark.circle.fill")
                                            .foregroundStyle(SOSoraColor.teal)
                                    }
                                }
                                .padding(12)
                                .background(condition == item ? SOSoraColor.cardRaised : SOSoraColor.field)
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                                        .stroke(condition == item ? SOSoraColor.teal : SOSoraColor.line, lineWidth: 1)
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Description · optional")
                        DarkField(placeholder: "Water depth, debris, who observed it…", text: $details, axis: .vertical)
                            .focused($focused)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Timestamp")
                        Text(SOSoraFormat.timestamp(observedAt))
                            .font(.body.weight(.semibold))
                            .foregroundStyle(SOSoraColor.text)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(14)
                            .background(SOSoraColor.field)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .stroke(SOSoraColor.line, lineWidth: 1)
                            )
                        OutlineButton(title: "Stamp with the current time", systemImage: "clock") {
                            observedAt = .now
                        }
                    }

                    coordinateSection

                    PhotoPickerField(photoData: $photoData)

                    SafetyNote(text: "Unverified field note. Saved on this phone first. Not a closure, a 911 call, or a radio message.")

                    TealButton(title: "Save report on this device", systemImage: "square.and.arrow.down") {
                        store.saveRoadReport(
                            segmentID: segment.id,
                            condition: condition,
                            details: details,
                            latitude: latitude,
                            longitude: longitude,
                            source: source,
                            observedAt: observedAt,
                            photoData: photoData
                        )
                        dismiss()
                    }
                }
                .padding(20)
                .padding(.bottom, 28)
            }
            .contentMargins(.bottom, 24, for: .scrollContent)
        }
        .navigationTitle("Road report")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Cancel") { dismiss() }
            }
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { focused = false }
            }
        }
        .onAppear {
            location.request()
            applyRoadCoordinate()
        }
        .onChange(of: location.latest) { _, _ in
            if deviceIsFar {
                applyRoadCoordinate()
            }
        }
    }

    private var roadPoint: GeoPoint { segment.midpoint }

    private var deviceDistance: Double? {
        guard let fix = location.latest else { return nil }
        return GeoDistance.meters(
            fix.coordinate.latitude,
            fix.coordinate.longitude,
            roadPoint.latitude,
            roadPoint.longitude
        )
    }

    private var deviceIsFar: Bool {
        guard let deviceDistance else { return false }
        return deviceDistance > GeoDistance.farFromRoad
    }

    private var coordinateSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            FieldLabel(text: "Selected road")
            coordinateRow(
                title: "Saved with \(segment.name)",
                value: SOSoraFormat.coordinate(roadPoint.latitude, roadPoint.longitude),
                emphasized: source == .road
            )
            FieldLabel(text: "This device")
            if let fix = location.latest, let deviceDistance {
                coordinateRow(
                    title: "Device GPS · \(GeoDistance.label(deviceDistance)) from this road",
                    value: SOSoraFormat.coordinate(fix.coordinate.latitude, fix.coordinate.longitude),
                    emphasized: source == .gps
                )
            } else {
                Text(location.message ?? "No GPS fix yet.")
                    .font(.footnote)
                    .foregroundStyle(SOSoraColor.muted)
            }
            if deviceIsFar {
                Text("This device is far from the selected road. The report keeps the road coordinate and does not use this GPS fix.")
                    .font(.footnote)
                    .foregroundStyle(SOSoraColor.amber)
                    .fixedSize(horizontal: false, vertical: true)
            } else if location.latest != nil {
                HStack(spacing: 8) {
                    OutlineButton(title: "Use device GPS", systemImage: "location.fill") {
                        guard let fix = location.latest, !deviceIsFar else { return }
                        latitude = fix.coordinate.latitude
                        longitude = fix.coordinate.longitude
                        source = .gps
                    }
                    OutlineButton(title: "Use selected road", systemImage: "road.lanes") {
                        applyRoadCoordinate()
                    }
                }
            } else {
                OutlineButton(title: "Check device GPS", systemImage: "location.fill") {
                    location.request()
                }
            }
        }
    }

    private func coordinateRow(title: String, value: String, emphasized: Bool) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption)
                .foregroundStyle(SOSoraColor.muted)
            Text(value)
                .font(.body.monospaced().weight(.semibold))
                .foregroundStyle(emphasized ? SOSoraColor.teal : SOSoraColor.text)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(emphasized ? SOSoraColor.teal.opacity(0.08) : SOSoraColor.field)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(emphasized ? SOSoraColor.teal.opacity(0.7) : SOSoraColor.line, lineWidth: 1)
        )
    }

    private func applyRoadCoordinate() {
        latitude = roadPoint.latitude
        longitude = roadPoint.longitude
        source = .road
    }

    private func color(for condition: RoadCondition) -> Color {
        switch condition {
        case .passable: SOSoraColor.teal
        case .blocked: SOSoraColor.coral
        case .unknown: SOSoraColor.amber
        }
    }
}

struct RecentReportsView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        SOSoraScreen {
            if store.roadReports.isEmpty {
                VStack(spacing: 8) {
                    Text("No road reports yet")
                        .font(.headline)
                        .foregroundStyle(SOSoraColor.text)
                    Text("Select a road on the map and save what you observe.")
                        .font(.subheadline)
                        .foregroundStyle(SOSoraColor.muted)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List {
                    ForEach(store.roadReports) { report in
                        NavigationLink(value: ResponderRoute.report(report.id)) {
                            RoadReportCard(report: report)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                        .listRowInsets(EdgeInsets(top: 6, leading: 20, bottom: 6, trailing: 20))
                        .swipeActions {
                            if !report.isSimulated {
                                Button(role: .destructive) {
                                    store.deleteRoadReport(id: report.id)
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
        .navigationTitle("Recent reports")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                RoleSwitchButton()
            }
        }
    }
}

struct RoadReportCard: View {
    var report: RoadConditionReport

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(DemoCatalog.road(id: report.segmentID)?.name ?? report.segmentID)
                    .font(.headline)
                    .foregroundStyle(SOSoraColor.text)
                Spacer()
                Text(SOSoraFormat.relative(report.observedAt))
                    .font(.caption)
                    .foregroundStyle(SOSoraColor.muted)
            }
            Text(report.details.isEmpty ? report.condition.detail : report.details)
                .font(.subheadline)
                .foregroundStyle(SOSoraColor.muted)
                .lineLimit(2)
            Text("\(report.coordinateSource.title) · \(SOSoraFormat.coordinate(report.latitude, report.longitude))")
                .font(.caption.monospaced())
                .foregroundStyle(SOSoraColor.muted)
            HStack(spacing: 6) {
                RecordTag(title: report.condition.title, color: SOSoraColor.road(report))
                if report.isSimulated {
                    RecordTag(title: "Simulated", color: SOSoraColor.purpleSim)
                }
                RecordTag(title: report.syncState.title, color: report.syncState == .synced ? SOSoraColor.teal : SOSoraColor.muted)
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

struct RoadReportDetailView: View {
    @Environment(AppStore.self) private var store
    var id: UUID

    var body: some View {
        SOSoraScreen {
            if let report = store.roadReport(id: id) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Eyebrow(text: "Field report")
                            Spacer()
                            if report.isSimulated {
                                RecordTag(title: "Simulated", color: SOSoraColor.purpleSim)
                            }
                        }
                        Text(DemoCatalog.road(id: report.segmentID)?.name ?? "Road")
                            .font(.system(size: 28, weight: .heavy, design: .rounded))
                            .foregroundStyle(SOSoraColor.text)
                        RecordTag(title: report.condition.title, color: SOSoraColor.road(report))
                        SavedPhotoView(filename: report.photoFilename)
                        detail("Condition", report.condition.detail)
                        detail("Description", report.details.isEmpty ? "None added" : report.details)
                        detail("Observed", SOSoraFormat.timestamp(report.observedAt))
                        detail("Coordinate", "\(SOSoraFormat.coordinate(report.latitude, report.longitude))\n\(report.coordinateSource.title)")
                        detail("Verification", report.verification == "verified" ? "Verified flag" : "Unverified")
                        detail("Delivery", report.syncMessage ?? report.syncState.title)
                        Text("Unknown means unreported, not safe and not closed. A passable or blocked mark is only what was saved in this demonstration.")
                            .font(.footnote)
                            .foregroundStyle(SOSoraColor.muted)
                    }
                    .padding(20)
                }
            } else {
                Text("This report is no longer on this device.")
                    .foregroundStyle(SOSoraColor.muted)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .navigationTitle("Report")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func detail(_ title: String, _ value: String) -> some View {
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
}
