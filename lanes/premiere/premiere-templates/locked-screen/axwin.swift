import Cocoa
let pid = pid_t(CommandLine.arguments[1])!
let app = AXUIElementCreateApplication(pid)
func attr(_ e: AXUIElement, _ a: String) -> CFTypeRef? { var v: CFTypeRef?; AXUIElementCopyAttributeValue(e, a as CFString, &v); return v }
func dump(_ e: AXUIElement, _ d: Int) {
  let role = attr(e, kAXRoleAttribute) as? String ?? "?", title = attr(e, kAXTitleAttribute) as? String ?? "", desc = attr(e, kAXDescriptionAttribute) as? String ?? ""
  let val = (attr(e, kAXValueAttribute) as? String) ?? ""
  print(String(repeating: " ", count: d*2), role, title.isEmpty ? "" : "[\(title)]", desc.isEmpty ? "" : "{\(desc)}", val.isEmpty ? "" : "=\(val.prefix(60))")
  if d < 6, let ks = attr(e, kAXChildrenAttribute) as? [AXUIElement] { for k in ks.prefix(40) { dump(k, d+1) } }
}
for key in [kAXWindowsAttribute, kAXFocusedWindowAttribute, kAXMainWindowAttribute] {
  if let w = attr(app, key) { if let ws = w as? [AXUIElement] { print(key, ws.count); for x in ws { dump(x, 1) } } else { print(key, "1"); dump(w as! AXUIElement, 1) } } else { print(key, "none") }
}
