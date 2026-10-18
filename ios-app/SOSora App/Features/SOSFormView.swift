//
//  SOSFormView.swift
//  SOSora App
//

import SwiftUI

struct SOSFormView: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var emergencyType: EmergencyType = .floodRescue
    @State private var people = 2
    @State private var place = ""
    @State private var latitude = DemoArea.latitude
    @State private var longitude = DemoArea.longitude
    @State private var source: CoordinateSource = .approximateArea
    @State private var approximate = true
    @State private var details = ""
    @State private var error: String?
    @FocusState private var focused: Bool

    var body: some View {
        SOSoraScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Emergency type")
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 148), spacing: 8)], spacing: 8) {
                            ForEach(EmergencyType.allCases) { type in
                                ChoiceChip(
                                    title: type.rawValue,
                                    systemImage: type.symbol,
                                    selected: emergencyType == type
                                ) {
                                    emergencyType = type
                                }
                            }
                        }
                    }

                    LocationEditor(
                        place: $place,
                        latitude: $latitude,
                        longitude: $longitude,
                        source: $source,
                        approximate: $approximate
                    )

                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Number of people")
                        HStack {
                            stepButton(systemImage: "minus", enabled: people > 1) { people -= 1 }
                            Text("\(people)")
                                .font(.system(size: 28, weight: .heavy, design: .rounded))
                                .foregroundStyle(SOSoraColor.text)
                                .frame(maxWidth: .infinity)
                            stepButton(systemImage: "plus", enabled: people < 100) { people += 1 }
                        }
                        .padding(8)
                        .background(SOSoraColor.field)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .stroke(SOSoraColor.line, lineWidth: 1)
                        )
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Description · optional")
                        DarkField(placeholder: "What is happening, and what do you need?", text: $details, axis: .vertical)
                            .focused($focused)
                    }

                    InlineError(text: error)
                    SafetyNote(text: "Saved on this phone and offered to the demo server. Not sent to emergency services.")

                    Button(action: submit) {
                        Text("Save SOS on this device")
                            .font(.system(size: 17, weight: .heavy, design: .rounded))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .foregroundStyle(.white)
                            .background(SOSoraColor.coral)
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
                .padding(20)
                .padding(.bottom, 20)
            }
            .padding(.bottom, 72)
        }
        .navigationTitle("Request Help")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { focused = false }
            }
        }
    }

    private func stepButton(systemImage: String, enabled: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.headline.weight(.bold))
                .frame(width: 44, height: 44)
                .foregroundStyle(enabled ? SOSoraColor.tealInk : SOSoraColor.muted)
                .background(enabled ? SOSoraColor.teal : SOSoraColor.card)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
    }

    private func submit() {
        let trimmed = place.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2 else {
            error = "Enter a location with at least a street or place name."
            return
        }
        guard (1...100).contains(people) else {
            error = "Enter between 1 and 100 people."
            return
        }
        error = nil
        store.saveSOS(
            type: emergencyType,
            people: people,
            place: trimmed,
            latitude: latitude,
            longitude: longitude,
            source: source,
            approximate: approximate,
            details: details
        )
        dismiss()
    }
}

struct HazardFormView: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var kind: HazardKind = .flooding
    @State private var place = ""
    @State private var latitude = DemoArea.latitude
    @State private var longitude = DemoArea.longitude
    @State private var source: CoordinateSource = .approximateArea
    @State private var approximate = true
    @State private var details = ""
    @State private var photoData: Data?
    @State private var error: String?
    @FocusState private var focused: Bool

    var body: some View {
        SOSoraScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Hazard")
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 148), spacing: 8)], spacing: 8) {
                            ForEach(HazardKind.allCases) { item in
                                ChoiceChip(title: item.title, systemImage: item.symbol, selected: kind == item) {
                                    kind = item
                                }
                            }
                        }
                    }

                    LocationEditor(
                        place: $place,
                        latitude: $latitude,
                        longitude: $longitude,
                        source: $source,
                        approximate: $approximate
                    )

                    VStack(alignment: .leading, spacing: 8) {
                        FieldLabel(text: "Description · optional")
                        DarkField(placeholder: "What did you see, and is anything blocking the road?", text: $details, axis: .vertical)
                            .focused($focused)
                    }

                    PhotoPickerField(photoData: $photoData)

                    InlineError(text: error)
                    SafetyNote(text: "Stored on this phone. The demo API has no hazard route, and this is not a radio message.")

                    TealButton(title: "Save hazard on this device", systemImage: "square.and.arrow.down") {
                        submit()
                    }
                }
                .padding(20)
                .padding(.bottom, 20)
            }
            .padding(.bottom, 72)
        }
        .navigationTitle("Report Roads")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { focused = false }
            }
        }
    }

    private func submit() {
        let trimmed = place.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2 else {
            error = "Enter a location with at least a street or place name."
            return
        }
        error = nil
        store.saveHazard(
            kind: kind,
            place: trimmed,
            latitude: latitude,
            longitude: longitude,
            source: source,
            approximate: approximate,
            details: details,
            photoData: photoData
        )
        dismiss()
    }
}
