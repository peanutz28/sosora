//
//  LocationProvider.swift
//  SOSora App
//

import Foundation
import CoreLocation
import Observation

@Observable
final class LocationProvider: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()

    var latest: CLLocation?
    var authorization: CLAuthorizationStatus
    var message: String?

    override init() {
        authorization = manager.authorizationStatus
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyNearestTenMeters
    }

    func request() {
        message = nil
        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .denied, .restricted:
            message = "Location access is off. Type a place, or allow location for SOSora in Settings."
        @unknown default:
            message = "Location is unavailable. Type a place instead."
        }
    }

    func placeName(for location: CLLocation) async -> String? {
        let geocoder = CLGeocoder()
        guard let placemark = try? await geocoder.reverseGeocodeLocation(location).first else {
            return nil
        }
        let parts = [placemark.subThoroughfare, placemark.thoroughfare, placemark.locality]
            .compactMap { $0 }
            .filter { !$0.isEmpty }
        if parts.isEmpty { return placemark.name }
        return parts.joined(separator: " ")
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        let approved = status == .authorizedAlways || status == .authorizedWhenInUse
        Task { @MainActor in
            self.authorization = status
            if approved {
                self.manager.requestLocation()
            } else if status == .denied || status == .restricted {
                self.message = "Location access is off. Type a place, or allow location for SOSora in Settings."
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        Task { @MainActor in
            self.latest = location
            self.message = nil
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        let text = "GPS could not be read. You can still type a location."
        Task { @MainActor in
            if self.latest == nil {
                self.message = text
            }
            _ = error
        }
    }
}
