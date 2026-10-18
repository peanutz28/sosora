//
//  Models.swift
//  SOSora App
//

import Foundation
import CoreLocation

enum AppMode: String, Codable {
    case resident
    case responder
}

enum EmergencyType: String, Codable, CaseIterable, Identifiable {
    case floodRescue = "Flood rescue"
    case medical = "Medical"
    case trapped = "Trapped or stranded"
    case fire = "Fire"
    case structural = "Structural damage"
    case welfare = "Welfare check"
    case other = "Other"

    var id: String { rawValue }

    var symbol: String {
        switch self {
        case .floodRescue: "water.waves"
        case .medical: "cross.case.fill"
        case .trapped: "figure.wave"
        case .fire: "flame.fill"
        case .structural: "house.fill"
        case .welfare: "person.2.fill"
        case .other: "ellipsis.circle.fill"
        }
    }

    static func inferred(from message: String) -> EmergencyType {
        let text = message.lowercased()
        return allCases.first { text.contains($0.rawValue.lowercased()) } ?? .other
    }
}

enum SOSStatus: String, Codable, CaseIterable, Identifiable {
    case queued = "Queued"
    case received = "Received"
    case acknowledged = "Acknowledged"
    case underReview = "Under review"
    case resolved = "Resolved"

    var id: String { rawValue }

    init?(serverValue: String) {
        switch serverValue {
        case "Queued": self = .queued
        case "Received": self = .received
        case "Acknowledged": self = .acknowledged
        case "Under review": self = .underReview
        case "Resolved": self = .resolved
        default: return nil
        }
    }
}

enum Priority: String, Codable {
    case critical
    case high

    var title: String { rawValue.capitalized }

    static func inferred(type: EmergencyType, people: Int) -> Priority {
        if people >= 4 || type == .medical || type == .trapped || type == .fire {
            return .critical
        }
        return .high
    }
}

enum SyncState: String, Codable {
    case localOnly
    case pending
    case synced
    case failed

    var title: String {
        switch self {
        case .localOnly: "On this device"
        case .pending: "Waiting to sync"
        case .synced: "Demo server accepted"
        case .failed: "Not uploaded"
        }
    }
}

enum CoordinateSource: String, Codable {
    case gps
    case road
    case approximateArea
    case demo

    var title: String {
        switch self {
        case .gps: "GPS fix"
        case .road: "Selected road"
        case .approximateArea: "Approximate demo area"
        case .demo: "Simulated coordinate"
        }
    }
}

enum HazardKind: String, Codable, CaseIterable, Identifiable {
    case flooding
    case debris
    case bridge
    case powerLines
    case washout
    case landslide
    case other

    var id: String { rawValue }

    var title: String {
        switch self {
        case .flooding: "Flooding"
        case .debris: "Debris"
        case .bridge: "Bridge damage"
        case .powerLines: "Downed lines"
        case .washout: "Washout"
        case .landslide: "Landslide"
        case .other: "Other"
        }
    }

    var symbol: String {
        switch self {
        case .flooding: "water.waves"
        case .debris: "trash.slash"
        case .bridge: "building.columns.fill"
        case .powerLines: "bolt.slash.fill"
        case .washout: "drop.triangle.fill"
        case .landslide: "mountain.2.fill"
        case .other: "exclamationmark.triangle.fill"
        }
    }
}

enum RoadCondition: String, Codable, CaseIterable, Identifiable {
    case passable
    case blocked
    case unknown

    var id: String { rawValue }

    var title: String {
        switch self {
        case .passable: "Passable"
        case .blocked: "Blocked"
        case .unknown: "Unknown"
        }
    }

    var detail: String {
        switch self {
        case .passable: "Observed open when this report was saved"
        case .blocked: "Observed blocked when this report was saved"
        case .unknown: "No condition. Unknown means unreported, not safe"
        }
    }

    var symbol: String {
        switch self {
        case .passable: "checkmark.circle.fill"
        case .blocked: "xmark.octagon.fill"
        case .unknown: "questionmark.circle.fill"
        }
    }
}

struct GeoPoint: Codable, Hashable {
    var latitude: Double
    var longitude: Double

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }

    var location: CLLocation {
        CLLocation(latitude: latitude, longitude: longitude)
    }
}

struct RoadSegment: Identifiable, Codable, Hashable {
    var id: String
    var name: String
    var summary: String
    var coordinates: [GeoPoint]

    var midpoint: GeoPoint {
        guard !coordinates.isEmpty else {
            return GeoPoint(latitude: DemoArea.latitude, longitude: DemoArea.longitude)
        }
        let latitude = coordinates.map(\.latitude).reduce(0, +) / Double(coordinates.count)
        let longitude = coordinates.map(\.longitude).reduce(0, +) / Double(coordinates.count)
        return GeoPoint(latitude: latitude, longitude: longitude)
    }

    func distance(to coordinate: CLLocationCoordinate2D) -> CLLocationDistance {
        guard coordinates.count >= 2 else {
            return midpoint.location.distance(from: CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude))
        }
        var best = CLLocationDistance.greatestFiniteMagnitude
        for index in 0..<(coordinates.count - 1) {
            best = min(best, Self.distance(from: coordinate, toSegmentFrom: coordinates[index].coordinate, to: coordinates[index + 1].coordinate))
        }
        return best
    }

    private static func distance(
        from point: CLLocationCoordinate2D,
        toSegmentFrom start: CLLocationCoordinate2D,
        to end: CLLocationCoordinate2D
    ) -> CLLocationDistance {
        let latScale = 111_320.0
        let lngScale = 111_320.0 * cos(point.latitude * .pi / 180)
        func xy(_ coordinate: CLLocationCoordinate2D) -> (Double, Double) {
            (
                (coordinate.longitude - point.longitude) * lngScale,
                (coordinate.latitude - point.latitude) * latScale
            )
        }
        let a = xy(start)
        let b = xy(end)
        let dx = b.0 - a.0
        let dy = b.1 - a.1
        let lengthSquared = dx * dx + dy * dy
        if lengthSquared < 1 {
            return hypot(a.0, a.1)
        }
        let t = min(1, max(0, ((-a.0) * dx + (-a.1) * dy) / lengthSquared))
        return hypot(a.0 + t * dx, a.1 + t * dy)
    }
}

struct SOSRequest: Identifiable, Codable, Hashable {
    var id: String
    var emergencyType: EmergencyType
    var people: Int
    var place: String
    var latitude: Double
    var longitude: Double
    var coordinateSource: CoordinateSource
    var coordinateIsApproximate: Bool
    var details: String
    var status: SOSStatus
    var priority: Priority
    var syncState: SyncState
    var syncMessage: String?
    var createdAt: Date
    var isSimulated: Bool

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }

    var summary: String {
        let trimmed = details.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty { return emergencyType.rawValue }
        return trimmed
    }

    var apiMessage: String {
        let trimmed = details.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty { return "\(emergencyType.rawValue)." }
        return "\(emergencyType.rawValue). \(trimmed)"
    }
}

struct HazardReport: Identifiable, Codable, Hashable {
    var id: String
    var kind: HazardKind
    var place: String
    var latitude: Double
    var longitude: Double
    var coordinateSource: CoordinateSource
    var coordinateIsApproximate: Bool
    var details: String
    var photoFilename: String?
    var createdAt: Date
    var isSimulated: Bool

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

struct RoadConditionReport: Identifiable, Codable, Hashable {
    var id: UUID
    var segmentID: String
    var condition: RoadCondition
    var details: String
    var latitude: Double
    var longitude: Double
    var coordinateSource: CoordinateSource
    var observedAt: Date
    var photoFilename: String?
    var syncState: SyncState
    var syncMessage: String?
    var isSimulated: Bool
    var source: String
    var verification: String

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

enum DemoArea {
    static let latitude = 35.597
    static let longitude = -82.490
    static let place = "Swannanoa demonstration area"
}

enum GeoDistance {
    /// A device fix farther than this from the selected road is not that road's location.
    static let farFromRoad: Double = 1_500

    static func meters(_ latitude: Double, _ longitude: Double, _ otherLatitude: Double, _ otherLongitude: Double) -> Double {
        let start = CLLocation(latitude: latitude, longitude: longitude)
        let end = CLLocation(latitude: otherLatitude, longitude: otherLongitude)
        return start.distance(from: end)
    }

    static func label(_ meters: Double) -> String {
        if meters >= 10_000 {
            return String(format: "%.0f km", meters / 1_000)
        }
        if meters >= 1_000 {
            return String(format: "%.1f km", meters / 1_000)
        }
        return String(format: "%.0f m", meters)
    }
}

enum ResidentRoute: Hashable {
    case sosForm
    case roadMap
    case hazardForm
    case sos(String)
    case hazard(String)
}

enum ResponderRoute: Hashable {
    case report(UUID)
}
