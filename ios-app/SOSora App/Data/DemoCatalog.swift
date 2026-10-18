//
//  DemoCatalog.swift
//  SOSora App
//

import Foundation
import CoreLocation

enum DemoCatalog {
    static let mapCenter = GeoPoint(latitude: 35.597, longitude: -82.490)

    static let roads: [RoadSegment] = [
        RoadSegment(
            id: "demo-old-fort-hwy",
            name: "Old Fort Highway",
            summary: "Demonstration corridor through Swannanoa. Not a validated driving route.",
            coordinates: [
                GeoPoint(latitude: 35.590, longitude: -82.540),
                GeoPoint(latitude: 35.594, longitude: -82.510),
                GeoPoint(latitude: 35.600, longitude: -82.490),
                GeoPoint(latitude: 35.608, longitude: -82.475),
                GeoPoint(latitude: 35.606, longitude: -82.450),
                GeoPoint(latitude: 35.604, longitude: -82.420)
            ]
        ),
        RoadSegment(
            id: "demo-swannanoa-river",
            name: "Swannanoa River Road",
            summary: "Demonstration corridor near the seeded flood SOS. Not a validated driving route.",
            coordinates: [
                GeoPoint(latitude: 35.600, longitude: -82.470),
                GeoPoint(latitude: 35.6042, longitude: -82.4379),
                GeoPoint(latitude: 35.609, longitude: -82.420),
                GeoPoint(latitude: 35.612, longitude: -82.400)
            ]
        ),
        RoadSegment(
            id: "demo-broad-river",
            name: "Broad River Road",
            summary: "Demonstration corridor for the seeded isolation report.",
            coordinates: [
                GeoPoint(latitude: 35.592, longitude: -82.530),
                GeoPoint(latitude: 35.584, longitude: -82.520),
                GeoPoint(latitude: 35.576, longitude: -82.511),
                GeoPoint(latitude: 35.568, longitude: -82.495)
            ]
        ),
        RoadSegment(
            id: "demo-i40",
            name: "I-40 corridor",
            summary: "Simplified demonstration line north of Swannanoa. Not the real interstate geometry.",
            coordinates: [
                GeoPoint(latitude: 35.620, longitude: -82.540),
                GeoPoint(latitude: 35.618, longitude: -82.490),
                GeoPoint(latitude: 35.612, longitude: -82.440),
                GeoPoint(latitude: 35.608, longitude: -82.390)
            ]
        ),
        RoadSegment(
            id: "demo-bee-tree",
            name: "Bee Tree Road",
            summary: "Demonstration local road south of US-70.",
            coordinates: [
                GeoPoint(latitude: 35.600, longitude: -82.490),
                GeoPoint(latitude: 35.590, longitude: -82.478),
                GeoPoint(latitude: 35.582, longitude: -82.460),
                GeoPoint(latitude: 35.576, longitude: -82.445)
            ]
        ),
        RoadSegment(
            id: "demo-warren-wilson",
            name: "Warren Wilson Road",
            summary: "Demonstration connector northeast of Swannanoa.",
            coordinates: [
                GeoPoint(latitude: 35.606, longitude: -82.450),
                GeoPoint(latitude: 35.616, longitude: -82.442),
                GeoPoint(latitude: 35.624, longitude: -82.430)
            ]
        ),
        RoadSegment(
            id: "demo-whitson",
            name: "Whitson Avenue",
            summary: "Short demonstration street off Old Fort Highway.",
            coordinates: [
                GeoPoint(latitude: 35.608, longitude: -82.475),
                GeoPoint(latitude: 35.602, longitude: -82.468),
                GeoPoint(latitude: 35.596, longitude: -82.460)
            ]
        ),
        RoadSegment(
            id: "demo-patton-cove",
            name: "Patton Cove Road",
            summary: "Demonstration road near the simulated rescue unit.",
            coordinates: [
                GeoPoint(latitude: 35.592, longitude: -82.524),
                GeoPoint(latitude: 35.584, longitude: -82.505),
                GeoPoint(latitude: 35.578, longitude: -82.488)
            ]
        ),
        RoadSegment(
            id: "demo-bridge-approach",
            name: "Bridge approach",
            summary: "Scenario geometry for the simulated bridge obstruction. Not an official closure.",
            coordinates: [
                GeoPoint(latitude: 35.596, longitude: -82.496),
                GeoPoint(latitude: 35.6003, longitude: -82.475),
                GeoPoint(latitude: 35.603, longitude: -82.457)
            ]
        ),
        RoadSegment(
            id: "demo-buckeye-cove",
            name: "Buckeye Cove Road",
            summary: "Demonstration road branching from Swannanoa River Road.",
            coordinates: [
                GeoPoint(latitude: 35.6042, longitude: -82.4379),
                GeoPoint(latitude: 35.598, longitude: -82.430),
                GeoPoint(latitude: 35.590, longitude: -82.418)
            ]
        ),
        RoadSegment(
            id: "demo-rescue-spur",
            name: "Rescue spur",
            summary: "Demonstration link from the simulated rescue unit to Old Fort Highway.",
            coordinates: [
                GeoPoint(latitude: 35.592, longitude: -82.524),
                GeoPoint(latitude: 35.594, longitude: -82.510),
                GeoPoint(latitude: 35.600, longitude: -82.490)
            ]
        )
    ]

    static func road(id: String) -> RoadSegment? {
        roads.first { $0.id == id }
    }

    static func nearestRoad(to coordinate: CLLocationCoordinate2D) -> RoadSegment? {
        roads.min { $0.distance(to: coordinate) < $1.distance(to: coordinate) }
    }

    static func seededSnapshot(now: Date = .now) -> Snapshot {
        let requests = [
            SOSRequest(
                id: "SOS-1042",
                emergencyType: .floodRescue,
                people: 4,
                place: "Swannanoa River Road",
                latitude: 35.6042,
                longitude: -82.4379,
                coordinateSource: .demo,
                coordinateIsApproximate: false,
                details: "Four people trapped upstairs. Water rising.",
                status: .received,
                priority: .critical,
                syncState: .localOnly,
                syncMessage: "Simulated record. It was not sent to emergency services.",
                createdAt: now.addingTimeInterval(-60 * 60 * 5),
                isSimulated: true
            ),
            SOSRequest(
                id: "SOS-1039",
                emergencyType: .medical,
                people: 2,
                place: "Old Fort Highway",
                latitude: 35.608,
                longitude: -82.475,
                coordinateSource: .demo,
                coordinateIsApproximate: false,
                details: "Two people need medical evacuation.",
                status: .acknowledged,
                priority: .high,
                syncState: .localOnly,
                syncMessage: "Simulated record. It was not sent to emergency services.",
                createdAt: now.addingTimeInterval(-60 * 60 * 8),
                isSimulated: true
            ),
            SOSRequest(
                id: "SOS-1036",
                emergencyType: .trapped,
                people: 7,
                place: "Broad River Road",
                latitude: 35.576,
                longitude: -82.511,
                coordinateSource: .demo,
                coordinateIsApproximate: false,
                details: "Seven residents cannot cross the flooded road.",
                status: .received,
                priority: .critical,
                syncState: .localOnly,
                syncMessage: "Simulated record. It was not sent to emergency services.",
                createdAt: now.addingTimeInterval(-60 * 60 * 11),
                isSimulated: true
            )
        ]

        let hazards = [
            HazardReport(
                id: "HZ-DEMO-1",
                kind: .flooding,
                place: "Swannanoa River Road",
                latitude: 35.6042,
                longitude: -82.4379,
                coordinateSource: .demo,
                coordinateIsApproximate: false,
                details: "Simulated floodwater across the roadway. Not a live observation.",
                photoFilename: nil,
                createdAt: now.addingTimeInterval(-60 * 60 * 4),
                isSimulated: true
            )
        ]

        let bridge = road(id: "demo-bridge-approach")?.midpoint
        let highway = road(id: "demo-old-fort-hwy")?.midpoint
        let roadReports = [
            RoadConditionReport(
                id: UUID(uuidString: "00000000-0000-0000-0000-000000000101") ?? UUID(),
                segmentID: "demo-bridge-approach",
                condition: .blocked,
                details: "Drill marking for the bridge-closure scenario. Not an observed field condition.",
                latitude: bridge?.latitude ?? 35.6003,
                longitude: bridge?.longitude ?? -82.475,
                coordinateSource: .demo,
                observedAt: now.addingTimeInterval(-60 * 40),
                photoFilename: nil,
                syncState: .localOnly,
                syncMessage: "Simulated record kept on this device.",
                isSimulated: true,
                source: "simulation",
                verification: "unverified"
            ),
            RoadConditionReport(
                id: UUID(uuidString: "00000000-0000-0000-0000-000000000102") ?? UUID(),
                segmentID: "demo-old-fort-hwy",
                condition: .passable,
                details: "Seeded demonstration that this corridor was marked passable. Not a safety verification.",
                latitude: highway?.latitude ?? 35.602,
                longitude: highway?.longitude ?? -82.48,
                coordinateSource: .demo,
                observedAt: now.addingTimeInterval(-60 * 90),
                photoFilename: nil,
                syncState: .localOnly,
                syncMessage: "Simulated record kept on this device.",
                isSimulated: true,
                source: "simulation",
                verification: "unverified"
            )
        ]

        return Snapshot(
            schema: 1,
            mode: nil,
            apiBaseURL: APIClient.defaultBaseURL,
            selectedRoadID: "demo-swannanoa-river",
            requests: requests,
            hazards: hazards,
            roadReports: roadReports
        )
    }
}

struct Snapshot: Codable {
    var schema: Int
    var mode: AppMode?
    var apiBaseURL: String
    var selectedRoadID: String?
    var requests: [SOSRequest]
    var hazards: [HazardReport]
    var roadReports: [RoadConditionReport]
}
