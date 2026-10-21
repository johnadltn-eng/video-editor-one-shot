import Cocoa
let pid = pid_t(CommandLine.arguments[1])!; let top = CommandLine.arguments[2]; let item = CommandLine.arguments[3]
let app = AXUIElementCreateApplication(pid)
func attr(_ e: AXUIElement, _ a: String) -> CFTypeRef? { var v: CFTypeRef?; AXUIElementCopyAttributeValue(e, a as CFString, &v); return v }
guard let bar = attr(app, kAXMenuBarAttribute) else { print("no menubar"); exit(1) }
let items = attr(bar as! AXUIElement, kAXChildrenAttribute) as! [AXUIElement]
for mi in items where (attr(mi, kAXTitleAttribute) as? String) == top {
  let menus = attr(mi, kAXChildrenAttribute) as! [AXUIElement]
  for menu in menus { for it in (attr(menu, kAXChildrenAttribute) as? [AXUIElement] ?? []) {
    if (attr(it, kAXTitleAttribute) as? String) == item { let r = AXUIElementPerformAction(it, kAXPressAction as CFString); print("pressed", top, ">", item, "result", r.rawValue); exit(0) } } }
}
print("not found")
