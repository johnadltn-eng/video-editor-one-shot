import Cocoa
let args = CommandLine.arguments
let pid = pid_t(args[1])!, wid = CGWindowID(UInt32(args[2])!)
let fx = Double(args[3])!, fy = Double(args[4])!   // fraction of window width/height
guard let list = CGWindowListCopyWindowInfo([.optionIncludingWindow], wid) as? [[String: Any]], let w = list.first,
      let b = w[kCGWindowBounds as String] as? [String: Double] else { print("no window"); exit(1) }
let p = CGPoint(x: b["X"]! + b["Width"]! * fx, y: b["Y"]! + b["Height"]! * fy)
print("bounds", b, "click", p)
for (t, ev) in [(CGEventType.mouseMoved, 0), (.leftMouseDown, 1), (.leftMouseUp, 1)] {
  let e = CGEvent(mouseEventSource: nil, mouseType: t, mouseCursorPosition: p, mouseButton: .left)!
  if ev == 1 { e.setIntegerValueField(.mouseEventClickState, value: 1) }
  e.postToPid(pid)
  usleep(60000)
}
print("posted")
