//
//  AppStore.swift
//  SOSora App
//

import Foundation
import Network
import Observation

@Observable
final class AppStore {
    var mode: AppMode?
    var apiBaseURL: String
    var selectedRoadID: String?
    var requests: [SOSRequest]
    var hazards: [HazardReport]
    var roadReports: [RoadConditionReport]
    var isOnline = false
    var serverReachable: Bool?
    var serverDetail = "Not checked yet."
    var isSyncing = false
    var toast: String?
    var persistenceError: String?

    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "sosora.connectivity")
    private var didStartMonitor = false
    private var toastToken = 0

    init(preview: Bool = false) {
        let snapshot = preview ? DemoCatalog.seededSnapshot() : (LocalStore.loadSnapshot() ?? DemoCatalog.seededSnapshot())
        mode = snapshot.mode
        apiBaseURL = snapshot.apiBaseURL
        selectedRoadID = snapshot.selectedRoadID
        requests = snapshot.requests.sorted { $0.createdAt > $1.createdAt }
        hazards = snapshot.hazards.sorted { $0.createdAt > $1.createdAt }
        roadReports = snapshot.roadReports.sorted { $0.observedAt > $1.observedAt }
        let repairedCoordinates = repairDistantRoadCoordinates()
        if !preview {
            if LocalStore.loadSnapshot() == nil || repairedCoordinates {
                persist()
            }
            startMonitor()
        }
    }

    var pendingCount: Int {
        requests.filter { $0.syncState == .pending }.count
            + roadReports.filter { $0.syncState == .pending }.count
    }

    var selectedRoad: RoadSegment? {
        guard let selectedRoadID else { return nil }
        return DemoCatalog.road(id: selectedRoadID)
    }

    func latestReport(for segmentID: String) -> RoadConditionReport? {
        roadReports
            .filter { $0.segmentID == segmentID }
            .max { $0.observedAt < $1.observedAt }
    }

    func request(id: String) -> SOSRequest? {
        requests.first { $0.id == id }
    }

    func hazard(id: String) -> HazardReport? {
        hazards.first { $0.id == id }
    }

    func roadReport(id: UUID) -> RoadConditionReport? {
        roadReports.first { $0.id == id }
    }

    func chooseMode(_ mode: AppMode) {
        self.mode = mode
        persist()
    }

    func leaveMode() {
        mode = nil
        persist()
    }

    func selectRoad(_ id: String) {
        selectedRoadID = id
        persist()
    }

    func saveAPIBaseURL(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let components = URLComponents(string: trimmed),
              let scheme = components.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              components.host != nil
        else {
            return "Use a full address such as http://127.0.0.1:3000."
        }
        apiBaseURL = trimmed
        serverReachable = nil
        serverDetail = "Address saved. Not checked yet."
        persist()
        return nil
    }

    func saveSOS(
        type: EmergencyType,
        people: Int,
        place: String,
        latitude: Double,
        longitude: Double,
        source: CoordinateSource,
        approximate: Bool,
        details: String
    ) {
        let request = SOSRequest(
            id: "SOS-\(UUID().uuidString.prefix(8))",
            emergencyType: type,
            people: people,
            place: place.trimmingCharacters(in: .whitespacesAndNewlines),
            latitude: latitude,
            longitude: longitude,
            coordinateSource: source,
            coordinateIsApproximate: approximate,
            details: details.trimmingCharacters(in: .whitespacesAndNewlines),
            status: .queued,
            priority: Priority.inferred(type: type, people: people),
            syncState: .pending,
            syncMessage: "Saved on this device. It will upload when the demo server accepts it.",
            createdAt: .now,
            isSimulated: false
        )
        requests.insert(request, at: 0)
        persist()
        showToast("SOS saved on this device. Not sent to emergency services.")
        Task { await syncNow(announce: false) }
    }

    func saveHazard(
        kind: HazardKind,
        place: String,
        latitude: Double,
        longitude: Double,
        source: CoordinateSource,
        approximate: Bool,
        details: String,
        photoData: Data?
    ) {
        var filename: String?
        if let photoData {
            do {
                filename = try LocalStore.savePhoto(photoData)
            } catch {
                persistenceError = "The photo could not be saved. The hazard text was still kept."
            }
        }
        let hazard = HazardReport(
            id: "HZ-\(UUID().uuidString.prefix(8))",
            kind: kind,
            place: place.trimmingCharacters(in: .whitespacesAndNewlines),
            latitude: latitude,
            longitude: longitude,
            coordinateSource: source,
            coordinateIsApproximate: approximate,
            details: details.trimmingCharacters(in: .whitespacesAndNewlines),
            photoFilename: filename,
            createdAt: .now,
            isSimulated: false
        )
        hazards.insert(hazard, at: 0)
        persist()
        showToast("Hazard saved on this device. The demo API has no hazard endpoint yet.")
    }

    func saveRoadReport(
        segmentID: String,
        condition: RoadCondition,
        details: String,
        latitude: Double,
        longitude: Double,
        source: CoordinateSource,
        observedAt: Date,
        photoData: Data?
    ) {
        var filename: String?
        if let photoData {
            do {
                filename = try LocalStore.savePhoto(photoData)
            } catch {
                persistenceError = "The photo could not be saved. The road report text was still kept."
            }
        }
        let anchored = anchoredCoordinate(
            segmentID: segmentID,
            latitude: latitude,
            longitude: longitude,
            source: source
        )
        let report = RoadConditionReport(
            id: UUID(),
            segmentID: segmentID,
            condition: condition,
            details: details.trimmingCharacters(in: .whitespacesAndNewlines),
            latitude: anchored.latitude,
            longitude: anchored.longitude,
            coordinateSource: anchored.source,
            observedAt: observedAt,
            photoFilename: filename,
            syncState: .pending,
            syncMessage: "Saved on this device. Waiting for the demo server.",
            isSimulated: false,
            source: "operator",
            verification: "unverified"
        )
        roadReports.insert(report, at: 0)
        roadReports.sort { $0.observedAt > $1.observedAt }
        persist()
        showToast("Road report saved on this device. It is unverified and was not sent by radio.")
        Task { await syncNow(announce: false) }
    }

    func deleteRequest(id: String) {
        requests.removeAll { $0.id == id && !$0.isSimulated }
        persist()
    }

    func deleteHazard(id: String) {
        if let hazard = hazards.first(where: { $0.id == id && !$0.isSimulated }) {
            LocalStore.deletePhoto(hazard.photoFilename)
        }
        hazards.removeAll { $0.id == id && !$0.isSimulated }
        persist()
    }

    func deleteRoadReport(id: UUID) {
        if let report = roadReports.first(where: { $0.id == id && !$0.isSimulated }) {
            LocalStore.deletePhoto(report.photoFilename)
        }
        roadReports.removeAll { $0.id == id && !$0.isSimulated }
        persist()
    }

    func restoreSimulatedRecords() {
        let seed = DemoCatalog.seededSnapshot()
        for request in seed.requests where !requests.contains(where: { $0.id == request.id }) {
            requests.append(request)
        }
        for hazard in seed.hazards where !hazards.contains(where: { $0.id == hazard.id }) {
            hazards.append(hazard)
        }
        for report in seed.roadReports where !roadReports.contains(where: { $0.id == report.id }) {
            roadReports.append(report)
        }
        requests.sort { $0.createdAt > $1.createdAt }
        hazards.sort { $0.createdAt > $1.createdAt }
        roadReports.sort { $0.observedAt > $1.observedAt }
        persist()
        showToast("Simulated records restored. Your own reports were kept.")
    }

    func testConnection() async {
        await syncNow(announce: true)
    }

    func syncNow(announce: Bool) async {
        guard !isSyncing else { return }
        isSyncing = true
        defer {
            isSyncing = false
            persist()
        }

        let client = APIClient(baseURLString: apiBaseURL)
        do {
            let health = try await client.health()
            serverReachable = health.ok
            let mode = health.mode ?? "unknown"
            serverDetail = health.ok
                ? "Demo server reachable. Mode: \(mode). This is not emergency dispatch."
                : "The server responded, but it did not report a healthy demo mode."
            if !health.ok { return }
        } catch {
            serverReachable = false
            serverDetail = error.localizedDescription
            if announce {
                showToast("Demo server unreachable. Reports stay on this device.")
            }
            return
        }

        var uploaded = 0
        for index in requests.indices {
            guard requests[index].syncState == .pending, !requests[index].isSimulated else { continue }
            do {
                let saved = try await client.submitIncident(requests[index])
                requests[index].syncState = .synced
                requests[index].syncMessage = "Accepted by the demo server. Not emergency dispatch."
                if let status = saved.status.flatMap(SOSStatus.init(serverValue:)) {
                    requests[index].status = status
                } else if requests[index].status == .queued {
                    requests[index].status = .received
                }
                uploaded += 1
            } catch {
                requests[index].syncMessage = error.localizedDescription
                if let api = error as? APIError, !api.shouldRetry {
                    requests[index].syncState = .failed
                }
            }
        }

        let roadIndexes = roadReports.indices.filter { shouldUploadRoadReport(roadReports[$0]) }
        if !roadIndexes.isEmpty {
            do {
                let catalog = try await client.roadCatalog()
                for index in roadIndexes {
                    reconcileRoadCoordinate(at: index)
                    guard let road = DemoCatalog.road(id: roadReports[index].segmentID) else {
                        roadReports[index].syncState = .failed
                        roadReports[index].syncMessage = "Saved on this device. This road is not in the local map."
                        continue
                    }
                    guard let match = RoadSegmentMatcher.match(road: road, catalog: catalog) else {
                        roadReports[index].syncState = .failed
                        roadReports[index].syncMessage = "Saved on this device. The server road extract has no nearby segment named \(road.name), so this report was not uploaded. Photos stay on this device."
                        continue
                    }
                    do {
                        try await client.submitRoadReport(
                            roadReports[index],
                            serverSegmentID: match.id,
                            roadName: match.name ?? road.name
                        )
                        roadReports[index].syncState = .synced
                        roadReports[index].syncMessage = "Text report accepted for \(match.name ?? road.name). Photos stay on this device. Not a verified closure."
                        uploaded += 1
                    } catch {
                        roadReports[index].syncMessage = error.localizedDescription
                        if let api = error as? APIError, !api.shouldRetry {
                            roadReports[index].syncState = .failed
                        }
                    }
                }
            } catch {
                let message = (error as? APIError)?.isMissingRoute == true
                    ? "Saved on this device. This demo server does not expose road reports. Photos stay on this device."
                    : error.localizedDescription
                for index in roadIndexes {
                    roadReports[index].syncState = .failed
                    roadReports[index].syncMessage = message
                }
            }
        }

        if let state = try? await client.state() {
            merge(state)
        }

        if announce || uploaded > 0 {
            let roadHeld = roadReports.contains { !$0.isSimulated && $0.syncState == .failed }
            if uploaded > 0 {
                showToast("Demo server accepted \(uploaded) \(uploaded == 1 ? "report" : "reports").")
            } else if roadHeld {
                showToast("Road reports stayed on this device.")
            } else if pendingCount == 0 {
                showToast("Nothing waiting to upload.")
            } else {
                showToast("Still waiting. Reports remain on this device.")
            }
        }
    }

    func showToast(_ text: String) {
        toastToken += 1
        let token = toastToken
        toast = text
        Task {
            try? await Task.sleep(for: .seconds(3.2))
            guard token == toastToken else { return }
            toast = nil
        }
    }

    private func merge(_ state: StateDTO) {
        for remote in state.incidents {
            if let index = requests.firstIndex(where: { $0.id == remote.id }) {
                if let status = remote.status.flatMap(SOSStatus.init(serverValue:)) {
                    requests[index].status = status
                }
                if requests[index].syncState == .pending {
                    requests[index].syncState = .synced
                    requests[index].syncMessage = "Matched a record already on the demo server."
                }
                continue
            }
            guard let latitude = remote.lat, let longitude = remote.lng else { continue }
            let message = remote.message ?? remote.description ?? "Imported demo incident"
            let source = remote.source ?? ""
            let simulated = source == "seeded_simulation" || source == "scenario" || source.hasPrefix("seed")
            let request = SOSRequest(
                id: remote.id,
                emergencyType: EmergencyType.inferred(from: message),
                people: remote.people ?? 1,
                place: remote.place ?? "Imported location",
                latitude: latitude,
                longitude: longitude,
                coordinateSource: .demo,
                coordinateIsApproximate: false,
                details: message,
                status: remote.status.flatMap(SOSStatus.init(serverValue:)) ?? .received,
                priority: remote.priority == "critical" ? .critical : .high,
                syncState: .synced,
                syncMessage: "Imported from the demo server.",
                createdAt: SOSoraDateParser.parse(remote.created_at) ?? .now,
                isSimulated: simulated
            )
            requests.append(request)
        }
        requests.sort { $0.createdAt > $1.createdAt }
    }

    private func shouldUploadRoadReport(_ report: RoadConditionReport) -> Bool {
        guard !report.isSimulated else { return false }
        return report.syncState == .pending || report.syncState == .failed
    }

    private func anchoredCoordinate(
        segmentID: String,
        latitude: Double,
        longitude: Double,
        source: CoordinateSource
    ) -> (latitude: Double, longitude: Double, source: CoordinateSource) {
        guard let road = DemoCatalog.road(id: segmentID) else {
            return (latitude, longitude, source)
        }
        let separation = GeoDistance.meters(latitude, longitude, road.midpoint.latitude, road.midpoint.longitude)
        guard separation > GeoDistance.farFromRoad else {
            return (latitude, longitude, source)
        }
        return (road.midpoint.latitude, road.midpoint.longitude, .road)
    }

    @discardableResult
    private func repairDistantRoadCoordinates() -> Bool {
        var changed = false
        for index in roadReports.indices where !roadReports[index].isSimulated {
            let before = roadReports[index].coordinateSource
            let latitude = roadReports[index].latitude
            let longitude = roadReports[index].longitude
            reconcileRoadCoordinate(at: index)
            if roadReports[index].coordinateSource != before
                || roadReports[index].latitude != latitude
                || roadReports[index].longitude != longitude {
                changed = true
            }
        }
        return changed
    }

    private func reconcileRoadCoordinate(at index: Int) {
        let report = roadReports[index]
        let anchored = anchoredCoordinate(
            segmentID: report.segmentID,
            latitude: report.latitude,
            longitude: report.longitude,
            source: report.coordinateSource
        )
        roadReports[index].latitude = anchored.latitude
        roadReports[index].longitude = anchored.longitude
        roadReports[index].coordinateSource = anchored.source
    }

    private func startMonitor() {
        guard !didStartMonitor else { return }
        didStartMonitor = true
        monitor.pathUpdateHandler = { path in
            let online = path.status == .satisfied
            Task { @MainActor in
                let wasOnline = self.isOnline
                self.isOnline = online
                if online && !wasOnline {
                    await self.syncNow(announce: false)
                }
                if !online {
                    self.serverReachable = false
                    self.serverDetail = "This phone has no usable connection. Reports stay on the device until a connection returns. SOSora does not transmit them by radio."
                }
            }
        }
        monitor.start(queue: monitorQueue)
    }

    private func persist() {
        let snapshot = Snapshot(
            schema: 1,
            mode: mode,
            apiBaseURL: apiBaseURL,
            selectedRoadID: selectedRoadID,
            requests: requests,
            hazards: hazards,
            roadReports: roadReports
        )
        do {
            try LocalStore.save(snapshot)
            persistenceError = nil
        } catch {
            persistenceError = "SOSora could not write its local save file."
        }
    }
}
