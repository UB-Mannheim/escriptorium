// Menu bar agent for the self-contained eScriptorium macOS bundle.
//
// Shows a status item with the current state and offers Open / Stop /
// Start / Show logs / Quit. Service control is delegated to the launcher
// script (Contents/MacOS/eScriptorium), which sits next to this binary.

import Cocoa

let proc = ProcessInfo.processInfo
let env = proc.environment
let dataDir = env["ESCR_DATA_DIR"] ?? NSHomeDirectory()
    + "/Library/Application Support/eScriptorium"
let pidDir = dataDir + "/pids"
let logDir = dataDir + "/logs"
let macosDir = URL(fileURLWithPath: proc.arguments[0]).deletingLastPathComponent()
let launcherPath = macosDir.appendingPathComponent("eScriptorium").path

func webPort() -> Int {
    if let s = try? String(contentsOfFile: pidDir + "/web.port", encoding: .utf8),
       let p = Int(s.trimmingCharacters(in: .whitespacesAndNewlines)) {
        return p
    }
    if let e = env["ESCR_WEB_PORT"], let p = Int(e) { return p }
    return 8000
}

func webIsUp(port: Int) -> Bool {
    let sem = DispatchSemaphore(value: 0)
    var up = false
    guard let url = URL(string: "http://127.0.0.1:\(port)/health") else { return false }
    let task = URLSession.shared.dataTask(with: url) { _, resp, _ in
        if let http = resp as? HTTPURLResponse, (200..<400).contains(http.statusCode) {
            up = true
        }
        sem.signal()
    }
    task.resume()
    _ = sem.wait(timeout: .now() + 3)
    return up
}

func runLauncher(_ args: [String]) {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: launcherPath)
    p.arguments = args
    p.environment = env
    p.standardOutput = FileHandle.nullDevice
    p.standardError = FileHandle.nullDevice
    try? p.run()
}

func registerPid() {
    if let old = try? String(contentsOfFile: pidDir + "/agent.pid", encoding: .utf8),
       let pid = Int32(old.trimmingCharacters(in: .whitespacesAndNewlines)), pid > 0 {
        if kill(pid, 0) == 0 || errno == EPERM {
            exit(0)
        }
    }
    try? FileManager.default.createDirectory(atPath: pidDir, withIntermediateDirectories: true)
    try? String(getpid()).write(toFile: pidDir + "/agent.pid", atomically: true, encoding: .utf8)
}

final class Agent: NSObject {
    let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    var statusText: NSMenuItem!
    var openItem: NSMenuItem!
    var toggleItem: NSMenuItem!
    var busy = false

    override init() {
        super.init()
        if let img = NSImage(systemSymbolName: "book", accessibilityDescription: "eScriptorium") {
            img.isTemplate = true
            statusItem.button?.image = img
        } else {
            statusItem.button?.title = "eS"
        }
        let menu = NSMenu()
        statusText = NSMenuItem(title: "eScriptorium", action: nil, keyEquivalent: "")
        statusText.isEnabled = false
        openItem = NSMenuItem(title: "Open eScriptorium", action: #selector(openWeb), keyEquivalent: "")
        openItem.target = self
        toggleItem = NSMenuItem(title: "…", action: #selector(toggle), keyEquivalent: "")
        toggleItem.target = self
        let logsItem = NSMenuItem(title: "Show logs", action: #selector(showLogs), keyEquivalent: "")
        logsItem.target = self
        let quitItem = NSMenuItem(title: "Quit eScriptorium",
                                  action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(statusText)
        menu.addItem(.separator())
        menu.addItem(openItem)
        menu.addItem(toggleItem)
        menu.addItem(logsItem)
        menu.addItem(.separator())
        menu.addItem(quitItem)
        statusItem.menu = menu
        registerPid()
        update()
        Timer.scheduledTimer(withTimeInterval: 4, repeats: true) { [weak self] _ in
            self?.update()
        }
    }

    func update() {
        DispatchQueue.global(qos: .utility).async { [weak self] in
            let up = FileManager.default.fileExists(atPath: dataDir) && webIsUp(port: webPort())
            DispatchQueue.main.async {
                guard let self else { return }
                if !FileManager.default.fileExists(atPath: dataDir) {
                    // Data directory was deleted (reset / test cleanup).
                    NSApplication.shared.terminate(nil)
                    return
                }
                self.statusText.title = up ? "eScriptorium is running" : "eScriptorium is stopped"
                self.openItem.isHidden = !up
                self.toggleItem.title = up ? "Stop eScriptorium" : "Start eScriptorium"
            }
        }
    }

    @objc func openWeb() {
        if let url = URL(string: "http://127.0.0.1:\(webPort())/") {
            NSWorkspace.shared.open(url)
        }
    }

    @objc func toggle() {
        guard !busy else { return }
        busy = true
        toggleItem.isEnabled = false
        let up = webIsUp(port: webPort())
        runLauncher(up ? ["stop"] : ["start"])
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 2) { [weak self] in
            DispatchQueue.main.async {
                self?.busy = false
                self?.toggleItem.isEnabled = true
                self?.update()
            }
        }
    }

    @objc func showLogs() {
        NSWorkspace.shared.open(URL(fileURLWithPath: logDir))
    }
}

let app = NSApplication.shared
let delegate = Agent()
app.setActivationPolicy(.accessory)
app.run()
