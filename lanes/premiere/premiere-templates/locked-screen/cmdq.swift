import Cocoa
let pid = pid_t(CommandLine.arguments[1])!; let code = CGKeyCode(UInt16(CommandLine.arguments[2])!)
let src = CGEventSource(stateID: .hidSystemState)
let cmdDown = CGEvent(keyboardEventSource: src, virtualKey: 55, keyDown: true)!; cmdDown.flags = .maskCommand; cmdDown.postToPid(pid); usleep(80000)
let kd = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: true)!; kd.flags = .maskCommand; kd.postToPid(pid); usleep(80000)
let ku = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: false)!; ku.flags = .maskCommand; ku.postToPid(pid); usleep(80000)
let cmdUp = CGEvent(keyboardEventSource: src, virtualKey: 55, keyDown: false)!; cmdUp.flags = []; cmdUp.postToPid(pid)
print("posted cmd+", code)
