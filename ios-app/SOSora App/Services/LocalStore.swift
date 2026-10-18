//
//  LocalStore.swift
//  SOSora App
//

import Foundation
import UIKit

enum LocalStore {
    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()

    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    static var directory: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let folder = base.appendingPathComponent("SOSora", isDirectory: true)
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder
    }

    static var snapshotURL: URL {
        directory.appendingPathComponent("snapshot.json")
    }

    static var photosDirectory: URL {
        let folder = directory.appendingPathComponent("photos", isDirectory: true)
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder
    }

    static func loadSnapshot() -> Snapshot? {
        guard let data = try? Data(contentsOf: snapshotURL) else { return nil }
        return try? decoder.decode(Snapshot.self, from: data)
    }

    static func save(_ snapshot: Snapshot) throws {
        let data = try encoder.encode(snapshot)
        try data.write(to: snapshotURL, options: .atomic)
    }

    static func savePhoto(_ data: Data) throws -> String {
        let filename = UUID().uuidString + ".jpg"
        let url = photosDirectory.appendingPathComponent(filename)
        let jpeg = compressedJPEG(data) ?? data
        try jpeg.write(to: url, options: .atomic)
        return filename
    }

    static func photoURL(_ filename: String) -> URL {
        photosDirectory.appendingPathComponent(filename)
    }

    static func image(named filename: String?) -> UIImage? {
        guard let filename else { return nil }
        return UIImage(contentsOfFile: photoURL(filename).path)
    }

    static func deletePhoto(_ filename: String?) {
        guard let filename else { return }
        try? FileManager.default.removeItem(at: photoURL(filename))
    }

    private static func compressedJPEG(_ data: Data) -> Data? {
        guard let image = UIImage(data: data) else { return nil }
        let maxSide: CGFloat = 1600
        let longest = max(image.size.width, image.size.height)
        let scale = longest > 0 ? min(1, maxSide / longest) : 1
        let size = CGSize(width: image.size.width * scale, height: image.size.height * scale)
        let format = UIGraphicsImageRendererFormat.default()
        format.scale = 1
        let renderer = UIGraphicsImageRenderer(size: size, format: format)
        let resized = renderer.image { _ in
            image.draw(in: CGRect(origin: .zero, size: size))
        }
        return resized.jpegData(compressionQuality: 0.72)
    }
}
