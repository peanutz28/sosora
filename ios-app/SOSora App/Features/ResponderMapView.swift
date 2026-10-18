//
//  ResponderMapView.swift
//  SOSora App
//

import SwiftUI
import MapKit

struct ResponderShell: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        TabView {
            ResponderMapView()
                .tabItem { Label("Map", systemImage: "map.fill") }

            NavigationStack {
                RecentReportsView()
                    .navigationDestination(for: ResponderRoute.self) { route in
                        if case .report(let id) = route {
                            RoadReportDetailView(id: id)
                        }
                    }
            }
            .tabItem {
                Label("Reports", systemImage: "list.bullet.rectangle")
            }
            .badge(store.pendingCount)

            NavigationStack {
                SyncStatusView()
            }
            .tabItem { Label("Sync", systemImage: "arrow.triangle.2.circlepath") }
        }
        .tint(SOSoraColor.teal)
    }
}

struct ResponderMapView: View {
    var showsBackButton = false

    @Environment(AppStore.self) private var store
    @Environment(LocationProvider.self) private var location
    @Environment(\.dismiss) private var dismiss
    @State private var position: MapCameraPosition = .region(
        MKCoordinateRegion(
            center: DemoCatalog.mapCenter.coordinate,
            span: MKCoordinateSpan(latitudeDelta: 0.09, longitudeDelta: 0.16)
        )
    )
    @State private var satellite = false
    @State private var showingRoads = false
    @State private var reportingRoad: RoadSegment?
    @State private var selection: MapSelection<String>?

    var body: some View {
        Map(position: $position, selection: $selection) {
            ForEach(DemoCatalog.roads) { road in
                MapPolyline(coordinates: road.coordinates.map(\.coordinate))
                    .stroke(lineColor(for: road), style: lineStyle(for: road))
                    .tag(road.id)
            }

            ForEach(store.requests) { request in
                Annotation(request.id, coordinate: request.coordinate) {
                    MapPin(symbol: "sos", color: SOSoraColor.coral)
                }
            }

            ForEach(store.hazards) { hazard in
                Annotation(hazard.kind.title, coordinate: hazard.coordinate) {
                    MapPin(symbol: "exclamationmark.triangle.fill", color: SOSoraColor.amber)
                }
            }

            Annotation("Rescue Unit 4", coordinate: CLLocationCoordinate2D(latitude: 35.592, longitude: -82.524)) {
                MapPin(symbol: "arrow.up.right", color: Color(red: 0.075, green: 0.541, blue: 0.643))
            }
        }
        .mapStyle(satellite ? .imagery(elevation: .flat) : .standard(elevation: .flat, pointsOfInterest: .excludingAll, showsTraffic: false))
        .mapControls {
            MapUserLocationButton()
            MapCompass()
            MapScaleView()
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            header
        }
        .safeAreaInset(edge: .bottom, spacing: 10) {
            roadCard
                .padding(.horizontal, 12)
                .padding(.bottom, 18)
        }
        .sheet(isPresented: $showingRoads) {
            RoadListSheet { road in
                showingRoads = false
                focus(road)
            }
        }
        .sheet(item: $reportingRoad) { road in
            NavigationStack {
                RoadReportFormView(segment: road)
            }
            .presentationDragIndicator(.visible)
        }
        .onChange(of: selection) { _, newValue in
            guard let id = newValue?.value, id != store.selectedRoadID, let road = DemoCatalog.road(id: id) else { return }
            focus(road, moveCamera: true, updateSelection: false)
        }
        .onAppear {
            if selection == nil, let id = store.selectedRoadID {
                selection = MapSelection(id)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                if showsBackButton {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "chevron.backward")
                            .font(.body.weight(.semibold))
                            .frame(width: 36, height: 36)
                    }
                    .accessibilityLabel("Back")
                }
                VStack(alignment: .leading, spacing: 2) {
                    Eyebrow(text: showsBackButton ? "Roads" : "Field responder")
                    Text("Road map")
                        .font(.system(size: 22, weight: .heavy, design: .rounded))
                        .foregroundStyle(SOSoraColor.text)
                }
                Spacer()
                RoleSwitchButton()
            }
            HStack(spacing: 8) {
                SimulationTag()
                Text(satellite ? "Satellite" : "Street")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(SOSoraColor.muted)
                Spacer()
                Button(satellite ? "Street" : "Satellite") {
                    satellite.toggle()
                }
                .font(.caption.weight(.bold))
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .foregroundStyle(SOSoraColor.text)
                .background(Color(red: 0.165, green: 0.341, blue: 0.376))
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 12)
        .background(SOSoraColor.header.opacity(0.96))
    }

    private var roadCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let road = store.selectedRoad {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Eyebrow(text: "Selected road")
                        Text(road.name)
                            .font(.system(size: 20, weight: .heavy, design: .rounded))
                            .foregroundStyle(SOSoraColor.text)
                    }
                    Spacer()
                    conditionTag(for: road)
                }
                Text(road.summary)
                    .font(.footnote)
                    .foregroundStyle(SOSoraColor.muted)
                    .fixedSize(horizontal: false, vertical: true)
                if let separation = deviceSeparation(from: road), separation > GeoDistance.farFromRoad {
                    Text("Device GPS is \(GeoDistance.label(separation)) from this road. A report here keeps the road coordinate.")
                        .font(.caption)
                        .foregroundStyle(SOSoraColor.amber)
                        .fixedSize(horizontal: false, vertical: true)
                }
                legend
                HStack(spacing: 8) {
                    Button("Report condition") {
                        reportingRoad = road
                    }
                    .font(.subheadline.weight(.heavy))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .foregroundStyle(SOSoraColor.tealInk)
                    .background(SOSoraColor.teal)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

                    Button {
                        showingRoads = true
                    } label: {
                        Image(systemName: "list.bullet")
                            .frame(width: 44, height: 44)
                            .foregroundStyle(SOSoraColor.text)
                            .background(SOSoraColor.field)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .stroke(SOSoraColor.line, lineWidth: 1)
                            )
                    }
                    .accessibilityLabel("Choose a road")
                }
                .buttonStyle(.plain)
            }
        }
        .padding(14)
        .background(SOSoraColor.panel.opacity(0.96))
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(SOSoraColor.line, lineWidth: 1)
        )
    }

    private var legend: some View {
        HStack(spacing: 10) {
            legendItem("Unknown", SOSoraColor.amber)
            legendItem("Passable", SOSoraColor.teal)
            legendItem("Blocked", SOSoraColor.coral)
            legendItem("Simulated", SOSoraColor.purpleSim)
        }
        .font(.caption2.weight(.semibold))
    }

    private func legendItem(_ title: String, _ color: Color) -> some View {
        HStack(spacing: 4) {
            Capsule().fill(color).frame(width: 14, height: 4)
            Text(title).foregroundStyle(SOSoraColor.muted)
        }
    }

    private func conditionTag(for road: RoadSegment) -> some View {
        let report = store.latestReport(for: road.id)
        let title = report?.condition.title ?? "Unknown"
        return RecordTag(title: title, color: SOSoraColor.road(report))
    }

    private func lineColor(for road: RoadSegment) -> Color {
        let report = store.latestReport(for: road.id)
        let quiet = report == nil || report?.isSimulated == true || report?.condition == .unknown
        if store.selectedRoadID == road.id {
            return Color.white.opacity(quiet ? 0.8 : 1)
        }
        return SOSoraColor.road(report).opacity(quiet ? 0.42 : 0.95)
    }

    private func lineStyle(for road: RoadSegment) -> StrokeStyle {
        let report = store.latestReport(for: road.id)
        let quiet = report == nil || report?.isSimulated == true || report?.condition == .unknown
        let selected = store.selectedRoadID == road.id
        return StrokeStyle(
            lineWidth: selected ? (quiet ? 3 : 4.5) : (quiet ? 1.6 : 3.5),
            lineCap: .round,
            lineJoin: .round,
            dash: quiet ? [3, 6] : []
        )
    }

    private func deviceSeparation(from road: RoadSegment) -> Double? {
        guard let fix = location.latest else { return nil }
        return GeoDistance.meters(
            fix.coordinate.latitude,
            fix.coordinate.longitude,
            road.midpoint.latitude,
            road.midpoint.longitude
        )
    }

    private func focus(_ road: RoadSegment, moveCamera: Bool = true, updateSelection: Bool = true) {
        store.selectRoad(road.id)
        if updateSelection {
            selection = MapSelection(road.id)
        }
        guard moveCamera else { return }
        let latitudes = road.coordinates.map(\.latitude)
        let longitudes = road.coordinates.map(\.longitude)
        guard let minLat = latitudes.min(), let maxLat = latitudes.max(),
              let minLng = longitudes.min(), let maxLng = longitudes.max() else { return }
        let region = MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: (minLat + maxLat) / 2, longitude: (minLng + maxLng) / 2),
            span: MKCoordinateSpan(
                latitudeDelta: max(0.02, (maxLat - minLat) * 1.8),
                longitudeDelta: max(0.02, (maxLng - minLng) * 1.8)
            )
        )
        withAnimation {
            position = .region(region)
        }
    }
}

struct MapPin: View {
    var symbol: String
    var color: Color

    var body: some View {
        Image(systemName: symbol)
            .font(.system(size: 11, weight: .bold))
            .foregroundStyle(.white)
            .frame(width: 28, height: 28)
            .background(color)
            .clipShape(Circle())
            .overlay(Circle().stroke(.white, lineWidth: 2))
            .shadow(color: .black.opacity(0.35), radius: 3, y: 2)
    }
}

struct RoadListSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    var onSelect: (RoadSegment) -> Void

    private var roads: [RoadSegment] {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return DemoCatalog.roads }
        return DemoCatalog.roads.filter {
            $0.name.localizedCaseInsensitiveContains(trimmed)
        }
    }

    var body: some View {
        NavigationStack {
            List(roads) { road in
                Button {
                    onSelect(road)
                } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(road.name)
                            .font(.headline)
                            .foregroundStyle(SOSoraColor.text)
                        Text(road.summary)
                            .font(.footnote)
                            .foregroundStyle(SOSoraColor.muted)
                            .lineLimit(2)
                    }
                    .padding(.vertical, 4)
                }
                .listRowBackground(SOSoraColor.card)
            }
            .scrollContentBackground(.hidden)
            .background(SOSoraColor.background)
            .navigationTitle("Demonstration roads")
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $query, prompt: "Search roads")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
        .presentationDragIndicator(.visible)
    }
}
