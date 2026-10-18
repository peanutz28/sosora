//
//  APIClient.swift
//  SOSora App
//
//  Client for the existing SOSora FastAPI demo. This file does not start a server
//  and does not implement radio transport.
//

import Foundation

struct APIClient {
    static let defaultBaseURL = "http://127.0.0.1:3000"

    var baseURLString: String
    private let session: URLSession

    init(baseURLString: String) {
        self.baseURLString = baseURLString
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 6
        configuration.waitsForConnectivity = false
        session = URLSession(configuration: configuration)
    }

    func health() async throws -> HealthDTO {
        try await get("api/health")
    }

    func state() async throws -> StateDTO {
        try await get("api/state")
    }

    func roadCatalog() async throws -> [ServerRoadSegment] {
        let catalog: RoadCatalogDTO = try await get("api/road-segments")
        return catalog.segments
    }

    func submitIncident(_ request: SOSRequest) async throws -> IncidentDTO {
        let body = IncidentBody(
            client_id: request.id,
            message: String(request.apiMessage.prefix(2000)),
            people: min(100, max(1, request.people)),
            place: String(request.place.prefix(180)),
            lat: request.latitude,
            lng: request.longitude
        )
        return try await send(path: "api/incidents", method: "POST", body: body)
    }

    func updateStatus(id: String, status: SOSStatus) async throws -> IncidentDTO {
        let body = StatusBody(status: status.rawValue)
        return try await send(path: "api/incidents/\(id)", method: "PATCH", body: body)
    }

    /// Uploads text to the existing `POST /api/road-reports` contract.
    /// `serverSegmentID` must already be an id from `GET /api/road-segments`.
    /// The API has no photo field, so images stay on the device.
    func submitRoadReport(
        _ report: RoadConditionReport,
        serverSegmentID: String,
        roadName: String
    ) async throws {
        let localName = DemoCatalog.road(id: report.segmentID)?.name ?? report.segmentID
        let evidence = [
            report.details.trimmingCharacters(in: .whitespacesAndNewlines),
            "Observed \(SOSoraFormat.timestamp(report.observedAt)).",
            "Selected road \(localName).",
            "Coordinate \(SOSoraFormat.coordinate(report.latitude, report.longitude)) (\(report.coordinateSource.title)).",
            "Matched server segment \(roadName).",
            report.photoFilename == nil ? "No photo." : "Photo kept on the device; this API stores text only."
        ]
        .filter { !$0.isEmpty }
        .joined(separator: " ")

        let body = RoadReportBody(
            segment_id: serverSegmentID,
            condition: report.condition.rawValue,
            source: "operator",
            evidence: String(evidence.prefix(2000)),
            verification: "unverified"
        )
        let (data, http) = try await request(path: "api/road-reports", method: "POST", body: try JSONEncoder().encode(body))
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.http(http.statusCode, Self.excerpt(data))
        }
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        let (data, http) = try await request(path: path, method: "GET", body: nil)
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.http(http.statusCode, Self.excerpt(data))
        }
        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIError.decoding
        }
    }

    private func send<Body: Encodable, Response: Decodable>(
        path: String,
        method: String,
        body: Body
    ) async throws -> Response {
        let (data, http) = try await request(path: path, method: method, body: try JSONEncoder().encode(body))
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.http(http.statusCode, Self.excerpt(data))
        }
        do {
            return try JSONDecoder().decode(Response.self, from: data)
        } catch {
            throw APIError.decoding
        }
    }

    private func request(path: String, method: String, body: Data?) async throws -> (Data, HTTPURLResponse) {
        let url = try endpoint(path)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 6
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw APIError.transport("The demo server did not return an HTTP response.")
            }
            return (data, http)
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.transport(error.localizedDescription)
        }
    }

    private func endpoint(_ path: String) throws -> URL {
        let trimmedBase = baseURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard var components = URLComponents(string: trimmedBase),
              let scheme = components.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              components.host != nil
        else {
            throw APIError.badURL
        }
        let trimmedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = "/" + trimmedPath
        components.query = nil
        components.fragment = nil
        guard let url = components.url else { throw APIError.badURL }
        return url
    }

    private static func excerpt(_ data: Data) -> String {
        let text = String(data: data, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if text.isEmpty { return "No response body." }
        return String(text.prefix(240))
    }
}

enum APIError: LocalizedError {
    case badURL
    case transport(String)
    case http(Int, String)
    case decoding

    var errorDescription: String? {
        switch self {
        case .badURL:
            "Enter a full http or https address for the demo server."
        case .transport(let message):
            "Could not reach the demo server. \(message)"
        case .http(let code, let body):
            "Demo server returned \(code). \(body)"
        case .decoding:
            "The demo server response could not be read."
        }
    }

    var shouldRetry: Bool {
        switch self {
        case .transport:
            true
        case .http(let code, _):
            code == 408 || code == 429 || code >= 500
        case .badURL, .decoding:
            false
        }
    }

    var isMissingRoute: Bool {
        guard case .http(let code, let body) = self, code == 404 else { return false }
        let text = body.lowercased()
        return !text.contains("segment") && !text.contains("extract")
    }
}

struct HealthDTO: Decodable {
    var ok: Bool
    var mode: String?
    var database: String?
}

struct StateDTO: Decodable {
    var stage: Int?
    var incidents: [IncidentDTO]
}

struct IncidentDTO: Decodable {
    var id: String
    var priority: String?
    var description: String?
    var place: String?
    var people: Int?
    var lat: Double?
    var lng: Double?
    var status: String?
    var message: String?
    var created_at: String?
    var source: String?
}

struct ServerRoadSegment: Decodable, Identifiable {
    var id: String
    var name: String?
    var lat: Double
    var lng: Double
}

struct RoadCatalogDTO: Decodable {
    var segments: [ServerRoadSegment]
}

enum RoadSegmentMatcher {
    /// Uses a catalog segment only when its name is the selected road and it sits near that road.
    /// A nearby segment with a different name is not treated as a match.
    static func match(road: RoadSegment, catalog: [ServerRoadSegment]) -> ServerRoadSegment? {
        let wanted = normalize(road.name)
        guard !wanted.isEmpty else { return nil }
        let named = catalog.filter { normalize($0.name ?? "") == wanted }
        guard let nearest = named.min(by: { distance($0, to: road.midpoint) < distance($1, to: road.midpoint) }) else {
            return nil
        }
        guard distance(nearest, to: road.midpoint) <= 1_200 else { return nil }
        return nearest
    }

    private static func normalize(_ name: String) -> String {
        name.lowercased()
            .replacingOccurrences(of: "[^a-z0-9]+", with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func distance(_ segment: ServerRoadSegment, to point: GeoPoint) -> Double {
        GeoDistance.meters(segment.lat, segment.lng, point.latitude, point.longitude)
    }
}

struct IncidentBody: Encodable {
    var client_id: String
    var message: String
    var people: Int
    var place: String
    var lat: Double
    var lng: Double
}

struct StatusBody: Encodable {
    var status: String
}

struct RoadReportBody: Encodable {
    var segment_id: String
    var condition: String
    var source: String
    var evidence: String
    var verification: String
}

enum SOSoraDateParser {
    static func parse(_ value: String?) -> Date? {
        guard let value else { return nil }
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = fractional.date(from: value) { return date }
        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        return plain.date(from: value)
    }
}
