//
//  PhotoPickerField.swift
//  SOSora App
//

import SwiftUI
import PhotosUI
import UIKit
import UniformTypeIdentifiers

struct PhotoPickerField: View {
    @Binding var photoData: Data?
    @State private var pickerItem: PhotosPickerItem?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            FieldLabel(text: "Photo · optional")
            if let photoData, let image = UIImage(data: photoData) {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(maxWidth: .infinity)
                    .frame(height: 180)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    .overlay(alignment: .topTrailing) {
                        Button {
                            self.photoData = nil
                            pickerItem = nil
                        } label: {
                            Image(systemName: "xmark")
                                .font(.caption.weight(.bold))
                                .foregroundStyle(SOSoraColor.text)
                                .padding(8)
                                .background(.black.opacity(0.55))
                                .clipShape(Circle())
                                .padding(8)
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Remove photo")
                    }
            }

            PhotosPicker(selection: $pickerItem, matching: .images) {
                Label(photoData == nil ? "Add a photo" : "Replace photo", systemImage: "photo")
                    .font(.subheadline.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .foregroundStyle(SOSoraColor.text)
                    .background(SOSoraColor.field)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .stroke(SOSoraColor.line, lineWidth: 1)
                    )
            }
            .buttonStyle(.plain)
            Text("Photos stay in this app. The demo server does not receive the image.")
                .font(.footnote)
                .foregroundStyle(SOSoraColor.muted)
        }
        .onChange(of: pickerItem) { _, item in
            guard let item else { return }
            Task {
                if let picked = try? await item.loadTransferable(type: PickedPhoto.self) {
                    photoData = picked.data
                }
            }
        }
    }
}

struct PickedPhoto: Transferable {
    let data: Data

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(importedContentType: .image) { data in
            PickedPhoto(data: data)
        }
    }
}

struct SavedPhotoView: View {
    var filename: String?

    var body: some View {
        if let image = LocalStore.image(named: filename) {
            Image(uiImage: image)
                .resizable()
                .scaledToFill()
                .frame(maxWidth: .infinity)
                .frame(height: 200)
                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
    }
}
