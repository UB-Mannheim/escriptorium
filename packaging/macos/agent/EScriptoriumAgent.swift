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
let statusFile = pidDir + "/status"
let launcherPidFile = pidDir + "/launcher.pid"
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

func launcherAlive() -> Bool {
    guard let s = try? String(contentsOfFile: launcherPidFile, encoding: .utf8),
          let p = Int32(s.trimmingCharacters(in: .whitespacesAndNewlines)), p > 0 else { return false }
    return kill(p, 0) == 0
}

func currentStatus() -> String {
    (try? String(contentsOfFile: statusFile, encoding: .utf8))?
        .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
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
    var phaseItem: NSMenuItem!
    var openItem: NSMenuItem!
    var toggleItem: NSMenuItem!
    var busy = false
    var launcherProc: Process?

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
        phaseItem = NSMenuItem(title: "", action: nil, keyEquivalent: "")
        phaseItem.isEnabled = false
        phaseItem.isHidden = true
        openItem = NSMenuItem(title: "Open eScriptorium", action: #selector(openWeb), keyEquivalent: "")
        openItem.target = self
        toggleItem = NSMenuItem(title: "…", action: #selector(toggle), keyEquivalent: "")
        toggleItem.target = self
        let logsItem = NSMenuItem(title: "Show logs", action: #selector(showLogs), keyEquivalent: "")
        logsItem.target = self
        let quitItem = NSMenuItem(title: "Quit eScriptorium",
                                  action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(statusText)
        menu.addItem(phaseItem)
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
            let dataDirExists = FileManager.default.fileExists(atPath: dataDir)
            let up = dataDirExists && webIsUp(port: webPort())
            let status = currentStatus()
            let starting = !up && launcherAlive() && !status.isEmpty
            DispatchQueue.main.async {
                guard let self else { return }
                if !dataDirExists {
                    // Data directory was deleted (reset / test cleanup).
                    NSApplication.shared.terminate(nil)
                    return
                }
                if up {
                    self.statusText.title = "eScriptorium is running"
                    self.phaseItem.isHidden = true
                } else if status == "failed to start" {
                    self.statusText.title = "eScriptorium failed to start"
                    self.phaseItem.isHidden = true
                } else if starting {
                    self.statusText.title = "eScriptorium is starting…"
                    self.phaseItem.title = status
                    self.phaseItem.isHidden = false
                } else {
                    self.statusText.title = "eScriptorium is stopped"
                    self.phaseItem.isHidden = true
                }
                self.openItem.isHidden = !up
                // While a stop/start is still running the toggle keeps its
                // "Stopping/Starting …" title and stays disabled; the same
                // applies while a launcher started by double-clicking the
                // app is still working through its startup phases.
                if self.busy || starting {
                    if !self.busy {
                        self.toggleItem.title = "Starting eScriptorium…"
                    }
                    self.toggleItem.isEnabled = false
                } else {
                    self.toggleItem.title = up ? "Stop eScriptorium" : "Start eScriptorium"
                    self.toggleItem.isEnabled = true
                }
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
        let up = webIsUp(port: webPort())
        toggleItem.title = up ? "Stopping eScriptorium…" : "Starting eScriptorium…"
        toggleItem.isEnabled = false
        let p = Process()
        p.executableURL = URL(fileURLWithPath: launcherPath)
        p.arguments = up ? ["stop"] : ["start"]
        p.environment = env
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        p.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async {
                guard let self else { return }
                self.busy = false
                self.launcherProc = nil
                self.toggleItem.isEnabled = true
                self.update()
            }
        }
        launcherProc = p
        do {
            try p.run()
        } catch {
            busy = false
            launcherProc = nil
            toggleItem.isEnabled = true
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
