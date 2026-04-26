import CoreGraphics
import Foundation

if CommandLine.arguments.count < 2 {
    exit(1)
}

guard let pid = Int32(CommandLine.arguments[1]) else {
    exit(1)
}

let options = CGWindowListOption([.optionOnScreenOnly, .excludeDesktopElements])
guard let windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
    exit(2)
}

for window in windows {
    guard let ownerPID = window[kCGWindowOwnerPID as String] as? Int,
          ownerPID == Int(pid),
          let layer = window[kCGWindowLayer as String] as? Int,
          layer == 0,
          let number = window[kCGWindowNumber as String] as? Int,
          let bounds = window[kCGWindowBounds as String] as? [String: Any],
          let width = bounds["Width"] as? Double,
          let height = bounds["Height"] as? Double,
          width > 32.0,
          height > 32.0 else {
        continue
    }
    print(number)
    exit(0)
}

exit(3)
