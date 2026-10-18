//
//  SOSoraTheme.swift
//  SOSora App
//

import SwiftUI
import UIKit

enum SOSoraColor {
    static let background = Color(red: 0.035, green: 0.075, blue: 0.110)
    static let header = Color(red: 0.043, green: 0.094, blue: 0.129)
    static let panel = Color(red: 0.063, green: 0.118, blue: 0.161)
    static let card = Color(red: 0.082, green: 0.149, blue: 0.192)
    static let cardRaised = Color(red: 0.094, green: 0.184, blue: 0.235)
    static let line = Color(red: 0.149, green: 0.224, blue: 0.278)
    static let text = Color(red: 0.929, green: 0.961, blue: 0.961)
    static let muted = Color(red: 0.569, green: 0.651, blue: 0.702)
    static let teal = Color(red: 0.318, green: 0.843, blue: 0.784)
    static let tealInk = Color(red: 0.031, green: 0.145, blue: 0.165)
    static let amber = Color(red: 1.000, green: 0.765, blue: 0.420)
    static let coral = Color(red: 1.000, green: 0.400, blue: 0.475)
    static let field = Color(red: 0.047, green: 0.098, blue: 0.137)
    static let purpleSim = Color(red: 0.753, green: 0.518, blue: 0.988)
    static let tag = Color(red: 0.725, green: 0.820, blue: 0.820)
    static let tagLine = Color(red: 0.314, green: 0.392, blue: 0.420)

    static func road(_ report: RoadConditionReport?) -> Color {
        guard let report, report.condition != .unknown else { return amber }
        if report.isSimulated { return purpleSim }
        switch report.condition {
        case .passable: return teal
        case .blocked: return coral
        case .unknown: return amber
        }
    }
}

enum SOSoraTheme {
    static func applyChrome() {
        let tab = UITabBarAppearance()
        tab.configureWithOpaqueBackground()
        tab.backgroundColor = UIColor(SOSoraColor.header)
        tab.stackedLayoutAppearance.normal.iconColor = UIColor(SOSoraColor.muted)
        tab.stackedLayoutAppearance.normal.titleTextAttributes = [.foregroundColor: UIColor(SOSoraColor.muted)]
        tab.stackedLayoutAppearance.selected.iconColor = UIColor(SOSoraColor.teal)
        tab.stackedLayoutAppearance.selected.titleTextAttributes = [.foregroundColor: UIColor(SOSoraColor.teal)]
        UITabBar.appearance().standardAppearance = tab
        UITabBar.appearance().scrollEdgeAppearance = tab

        let nav = UINavigationBarAppearance()
        nav.configureWithOpaqueBackground()
        nav.backgroundColor = UIColor(SOSoraColor.header)
        nav.titleTextAttributes = [.foregroundColor: UIColor(SOSoraColor.text)]
        nav.largeTitleTextAttributes = [.foregroundColor: UIColor(SOSoraColor.text)]
        UINavigationBar.appearance().standardAppearance = nav
        UINavigationBar.appearance().scrollEdgeAppearance = nav
        UINavigationBar.appearance().tintColor = UIColor(SOSoraColor.teal)
    }
}

enum SOSoraFormat {
    static func timestamp(_ date: Date) -> String {
        date.formatted(date: .abbreviated, time: .shortened)
    }

    static func relative(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: .now)
    }

    static func coordinate(_ latitude: Double, _ longitude: Double) -> String {
        String(format: "%.5f, %.5f", latitude, longitude)
    }

    static func people(_ count: Int) -> String {
        count == 1 ? "1 person" : "\(count) people"
    }
}

struct SOSoraScreen<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        content
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .background(SOSoraColor.background.ignoresSafeArea())
    }
}

struct BrandLockup: View {
    var compact = false

    var body: some View {
        HStack(spacing: 10) {
            Text("≋")
                .font(.system(size: compact ? 18 : 22, weight: .bold))
                .foregroundStyle(SOSoraColor.tealInk)
                .frame(width: compact ? 32 : 38, height: compact ? 32 : 38)
                .background(SOSoraColor.teal)
                .clipShape(RoundedRectangle(cornerRadius: compact ? 9 : 12, style: .continuous))
            VStack(alignment: .leading, spacing: 1) {
                HStack(alignment: .center, spacing: 0) {
                    Text("S")
                    CycloneMark()
                        .stroke(
                            SOSoraColor.teal,
                            style: StrokeStyle(lineWidth: compact ? 1.7 : 2.1, lineCap: .round, lineJoin: .round)
                        )
                        .frame(width: compact ? 13 : 17, height: compact ? 13 : 17)
                        .padding(.horizontal, compact ? 1 : 1.5)
                        .accessibilityHidden(true)
                    Text("S")
                    Text("ora").foregroundStyle(SOSoraColor.teal)
                }
                .font(.system(size: compact ? 20 : 26, weight: .heavy, design: .rounded))
                .foregroundStyle(SOSoraColor.text)
                if !compact {
                    Text("RESCUE INTELLIGENCE")
                        .font(.system(size: 10, weight: .bold))
                        .tracking(1.8)
                        .foregroundStyle(SOSoraColor.muted)
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("SOSora")
    }
}

struct CycloneMark: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let center = CGPoint(x: rect.midX, y: rect.midY)
        let radius = min(rect.width, rect.height) / 2
        let steps = 42
        for step in 0...steps {
            let progress = Double(step) / Double(steps)
            let angle = progress * 1.45 * 2 * Double.pi - Double.pi / 2
            let distance = radius * (0.16 + 0.84 * progress)
            let point = CGPoint(
                x: center.x + CGFloat(cos(angle) * distance),
                y: center.y + CGFloat(sin(angle) * distance)
            )
            if step == 0 {
                path.move(to: point)
            } else {
                path.addLine(to: point)
            }
        }
        return path
    }
}

struct Eyebrow: View {
    var text: String

    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 11, weight: .heavy))
            .tracking(1.6)
            .foregroundStyle(SOSoraColor.muted)
    }
}

struct SimulationTag: View {
    var body: some View {
        Text("SIMULATION")
            .font(.system(size: 10, weight: .bold))
            .tracking(1.1)
            .foregroundStyle(SOSoraColor.tag)
            .padding(.horizontal, 7)
            .padding(.vertical, 4)
            .overlay(
                RoundedRectangle(cornerRadius: 5, style: .continuous)
                    .stroke(SOSoraColor.tagLine, lineWidth: 1)
            )
            .accessibilityLabel("Simulation")
    }
}

struct RecordTag: View {
    var title: String
    var color: Color

    var body: some View {
        Text(title.uppercased())
            .font(.system(size: 10, weight: .heavy))
            .tracking(0.6)
            .foregroundStyle(color)
            .padding(.horizontal, 7)
            .padding(.vertical, 4)
            .background(color.opacity(0.12))
            .clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 5, style: .continuous)
                    .stroke(color.opacity(0.45), lineWidth: 1)
            )
    }
}

struct SafetyNote: View {
    var text: String

    var body: some View {
        Text(text)
            .font(.footnote)
            .foregroundStyle(SOSoraColor.muted)
            .fixedSize(horizontal: false, vertical: true)
    }
}

struct DisclaimerBanner: View {
    var text: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(SOSoraColor.amber)
                .padding(.top, 1)
            Text(text)
                .font(.footnote)
                .foregroundStyle(SOSoraColor.text)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(SOSoraColor.amber.opacity(0.10))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(SOSoraColor.amber.opacity(0.45), lineWidth: 1)
        )
    }
}

struct PanelCard<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(SOSoraColor.card)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(SOSoraColor.line, lineWidth: 1)
            )
    }
}

struct FieldLabel: View {
    var text: String

    var body: some View {
        Text(text)
            .font(.system(size: 12, weight: .semibold))
            .foregroundStyle(SOSoraColor.muted)
    }
}

struct DarkField: View {
    var placeholder: String
    @Binding var text: String
    var axis: Axis = .horizontal

    var body: some View {
        Group {
            if axis == .vertical {
                TextField(
                    "",
                    text: $text,
                    prompt: Text(placeholder).foregroundStyle(SOSoraColor.muted.opacity(0.8)),
                    axis: .vertical
                )
                .lineLimit(4...8)
            } else {
                TextField(
                    "",
                    text: $text,
                    prompt: Text(placeholder).foregroundStyle(SOSoraColor.muted.opacity(0.8))
                )
            }
        }
        .font(.body)
        .foregroundStyle(SOSoraColor.text)
        .padding(14)
        .background(SOSoraColor.field)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(SOSoraColor.line, lineWidth: 1)
        )
    }
}

struct TealButton: View {
    var title: String
    var systemImage: String?
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
            }
            .font(.system(size: 16, weight: .heavy, design: .rounded))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 15)
            .foregroundStyle(SOSoraColor.tealInk)
            .background(SOSoraColor.teal)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
    }
}

struct OutlineButton: View {
    var title: String
    var systemImage: String?
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
            }
            .font(.system(size: 15, weight: .semibold))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 13)
            .foregroundStyle(SOSoraColor.text)
            .background(SOSoraColor.header)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(SOSoraColor.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}

struct ChoiceChip: View {
    var title: String
    var systemImage: String
    var selected: Bool
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: systemImage)
                Text(title)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }
            .font(.system(size: 13, weight: .semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity)
            .foregroundStyle(selected ? SOSoraColor.tealInk : SOSoraColor.text)
            .background(selected ? SOSoraColor.teal : SOSoraColor.field)
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(selected ? SOSoraColor.teal : SOSoraColor.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

struct InlineError: View {
    var text: String?

    var body: some View {
        if let text, !text.isEmpty {
            Text(text)
                .font(.footnote)
                .foregroundStyle(SOSoraColor.coral)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

struct ToastBanner: View {
    var text: String

    var body: some View {
        Text(text)
            .font(.footnote.weight(.semibold))
            .foregroundStyle(SOSoraColor.text)
            .multilineTextAlignment(.center)
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(SOSoraColor.cardRaised.opacity(0.96))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(SOSoraColor.teal.opacity(0.5), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.35), radius: 16, y: 8)
            .padding(.horizontal, 20)
    }
}
