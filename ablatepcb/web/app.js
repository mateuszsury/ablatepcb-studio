let backend = null;
let analysis = null;
let selectedPreview = "top";
let lastLightBurnStatus = null;
let language = localStorage.getItem("ablatepcb-language") === "en" ? "en" : "pl";

const PL_EN = {
  "Studio masek PCB": "PCB mask studio",
  "Źródło": "Source", "Gerber ZIP lub katalog": "Gerber ZIP or folder",
  "Kontrola": "Review", "Warstwy i przelotki": "Layers and vias",
  "Ustawienie": "Setup", "Laminat i orientacja": "Board and orientation",
  "Eksport": "Export", "Pakiet LightBurn": "LightBurn package",
  "Program przygotowuje pliki, ale nigdy sam nie uruchamia lasera.": "The app prepares files but never starts the laser automatically.",
  "LOKALNE NARZĘDZIE PRODUKCYJNE": "LOCAL PRODUCTION TOOL",
  "Maski PCB bez ręcznej konwersji": "PCB masks without manual conversion",
  "Gotowy": "Ready", "Podgląd UI": "UI preview", "Przetwarzanie": "Processing",
  "Upuść paczkę produkcyjną.": "Drop your fabrication package.",
  "Rozpoznamy warstwy miedzi, obrys, wiercenia i przelotki. Pliki pozostają wyłącznie na tym komputerze.": "We detect copper layers, outline, drills, and vias. Files remain on this computer.",
  "Przeciągnij tutaj plik ZIP": "Drop a ZIP file here", "albo kliknij, aby wybrać archiwum": "or click to choose an archive",
  ".zip · folder Gerberów": ".zip · Gerber folder", "Wybierz rozpakowany katalog zamiast ZIP →": "Choose an extracted folder instead of ZIP →",
  "AKTYWNY PROJEKT": "ACTIVE PROJECT", "Zmień projekt": "Change project",
  "Łączenie…": "Connecting…", "Wykrywanie lokalnej aplikacji": "Detecting local application", "upłynęło": "elapsed", "pozostało": "remaining",
  "POZYCJA": "POSITION", "PRĘDKOŚĆ": "SPEED", "MOC": "POWER", "PRZEJŚCIA": "PASSES",
  "Zastosuj preset Pixi": "Apply Pixi preset", "Pauza": "Pause",
  "Otwórz / pokaż LightBurn": "Open / show LightBurn",
  "PROFIL STARTOWY · DOSTĘPNY BEZ GERBERA": "STARTING PROFILE · AVAILABLE WITHOUT GERBER",
  "Bez projektu preset zmienia tylko aktywną warstwę LightBurn. Po imporcie może także ustawić rozmiar i pozycję obrazu.": "Without a project, the preset changes only the active LightBurn layer. After import, it can also set image size and position.",
  "Potwierdzam poprawny Frame, położenie laminatu, wentylację i nadzór nad laserem.": "I confirm the Frame, board position, ventilation, and continuous laser supervision.",
  "PODGLĄD KONTROLNY": "CONTROL PREVIEW", "Geometria miedzi": "Copper geometry", "NAŁOŻENIE": "OVERLAY",
  "Podgląd pokazuje miedź na czarno. Plik wypalania ma odwrócone znaczenie.": "The preview shows copper in black. The ablation file uses the opposite meaning.",
  "WYMIAR PCB": "PCB SIZE", "z warstwy obrysu": "from outline layer", "PRZELOTKI": "VIAS",
  "MIN. APERTURA": "MIN. APERTURE", "kontrola rozdzielczości": "resolution check",
  "WALIDACJA": "VALIDATION", "Kontrole przed eksportem": "Pre-export checks", "Rozpoznane pliki warstw": "Detected layer files",
  "USTAWIENIE FIZYCZNE": "PHYSICAL SETUP", "Laminat na stole": "Board on the bed",
  "Szerokość laminatu": "Board width", "Wysokość laminatu": "Board height", "Lewy dolny X": "Lower-left X", "Lewy dolny Y": "Lower-left Y",
  "POZYCJA ŚRODKA W LIGHTBURN": "CENTER POSITION IN LIGHTBURN", "Jak przewracasz płytkę?": "How do you flip the board?",
  "Jak kartkę książki": "Like a book page", "odbicie lewo–prawo": "left-right mirror", "Jak kartkę kalendarza": "Like a calendar page", "odbicie góra–dół": "top-bottom mirror",
  "PROFIL STARTOWY": "STARTING PROFILE", "Pixi 5 W / farbowana miedź": "Pixi 5 W / painted copper",
  "Ustawienia trafią do instrukcji i raportu. Geometria pozostaje od nich niezależna.": "Settings are included in the instructions and report. Geometry remains independent.",
  "Prędkość": "Speed", "Moc": "Power", "Interwał": "Interval", "Przejścia": "Passes", "Overscan": "Overscan",
  "Gotowe do wygenerowania": "Ready to generate", "Napraw błędy blokujące": "Fix blocking errors",
  "PNG 1270 DPI + podglądy + wiercenia + raport": "PNG 1270 DPI + previews + drills + report",
  "Generuj pakiet LightBurn": "Generate LightBurn package",
  "PAKIET GOTOWY": "PACKAGE READY", "Możesz przejść do LightBurn.": "You can continue in LightBurn.",
  "Maski, alternatywne odbicie dolnej strony, przewodnik wiercenia i raport zostały zapisane w jednym katalogu.": "Masks, alternate bottom flip, drilling guide, and report were saved in one folder.",
  "Wczytaj TOP do LightBurn": "Load TOP into LightBurn", "Wczytaj BOTTOM": "Load BOTTOM", "Otwórz katalog": "Open folder", "Otwórz raport": "Open report", "← Wróć do projektu": "← Back to project",
  "Pracuję…": "Working…", "Analiza odbywa się lokalnie": "Analysis runs locally", "LightBurn offline": "LightBurn offline",
  "brak danych": "no data", "slotów": "slots", "Start wymaga potwierdzenia bezpieczeństwa.": "Start requires safety confirmation.",
  "Przed Start potwierdź Frame, położenie płytki, wentylację i nadzór.": "Before Start, confirm the Frame, board position, ventilation, and supervision.",
  "Uruchomić laser? Pozostań przy urządzeniu przez cały proces.": "Start the laser? Stay with the machine for the entire job.",
  "Polecenie wykonane.": "Command completed.", "Nieprawidłowe ustawienia generowania.": "Invalid generation settings.",
  "Najpierw wygeneruj pakiet LightBurn.": "Generate the LightBurn package first.", "Nieznana strona płytki.": "Unknown board side.",
  "Nieprawidłowy preset LightBurn.": "Invalid LightBurn preset.",
  "Zastosowano prędkość, moc, interwał i liczbę przejść do aktywnej warstwy LightBurn. Geometria nie została zmieniona.": "Speed, power, interval, and pass count were applied to the active LightBurn layer. Geometry was not changed.",
  "Zastosowano prędkość, moc, interwał, liczbę przejść, rozmiar i pozycję. Ustawienia obrazu korzystają z zapisanego profilu LightBurn.": "Speed, power, interval, pass count, size, and position were applied. Image settings use the saved LightBurn profile."
};
const EN_PL = Object.fromEntries(Object.entries(PL_EN).map(([pl, en]) => [en, pl]));

function translateValue(value) {
  const text = String(value);
  const polish = EN_PL[text] || text;
  if (language === "pl") return polish;
  if (PL_EN[polish]) return PL_EN[polish];
  return polish
    .replace(/^Wykryto (\d+) unikalnych przelotek\.$/, "Detected $1 unique vias.")
    .replace(/^(\d+) otworów ma średnicę poniżej 0,4 mm; wiercenie ręczne będzie trudne\.$/, "$1 holes are below 0.4 mm; manual drilling will be difficult.")
    .replace(/^Około ([\d,.]+) mm\.$/, "Approximately $1 mm.")
    .replace(/^Każda przelotka trafia w chronioną miedź TOP i BOTTOM\.$/, "Every via intersects protected TOP and BOTTOM copper.")
    .replace(/^Nie wykryto warstwy TOP copper\.$/, "TOP copper layer was not detected.")
    .replace(/^Projekt zostanie potraktowany jako jednostronny\.$/, "The project will be treated as single-sided.")
    .replace(/^Nie znaleziono osobnego pliku wierceń przelotek\.$/, "No separate via drill file was found.")
    .replace(/^Część renderu wychodzi poza obrys o więcej niż 0,05 mm\.$/, "Part of the render exceeds the outline by more than 0.05 mm.")
    .replace(/^Obrys PCB$/, "PCB outline").replace(/^Brak górnej miedzi$/, "Missing top copper").replace(/^Brak dolnej miedzi$/, "Missing bottom copper")
    .replace(/^Przelotki$/, "Vias").replace(/^Brak osobnej listy Via$/, "No separate via list").replace(/^Bardzo małe otwory$/, "Very small holes")
    .replace(/^Najmniejsza apertura miedzi$/, "Smallest copper aperture").replace(/^Pola przelotek$/, "Via pads").replace(/^Przelotka bez miedzi$/, "Via without copper");
}

function translateDocument() {
  document.documentElement.lang = language;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (["SCRIPT", "STYLE"].includes(node.parentElement?.tagName)) continue;
    const raw = node.nodeValue;
    const trimmed = raw.trim();
    if (!trimmed) continue;
    const translated = translateValue(trimmed);
    if (translated !== trimmed) node.nodeValue = raw.replace(trimmed, translated);
  }
  document.querySelectorAll("[data-lang]").forEach((button) => button.classList.toggle("active", button.dataset.lang === language));
  if (analysis) {
    renderChecks(); renderLayers(); updatePosition();
    $("exportStatus").textContent = translateValue(analysis.canGenerate ? "Gotowe do wygenerowania" : "Napraw błędy blokujące");
  }
  if (lastLightBurnStatus) renderLightBurnStatus(lastLightBurnStatus);
  if (backend?.setLanguage) backend.setLanguage(language);
}

document.querySelectorAll("[data-lang]").forEach((button) => button.addEventListener("click", () => {
  language = button.dataset.lang;
  localStorage.setItem("ablatepcb-language", language);
  translateDocument();
}));

const $ = (id) => document.getElementById(id);
const sourceView = $("sourceView");
const workspaceView = $("workspaceView");
const resultView = $("resultView");

function connectQtBackend() {
  new window.QWebChannel(qt.webChannelTransport, (channel) => {
    backend = channel.objects.backend;
    backend.analysisReady.connect(onAnalysis);
    backend.generationReady.connect(onGenerated);
    backend.errorOccurred.connect(showError);
    backend.busyChanged.connect(setBusy);
    backend.lightBurnStatus.connect(onLightBurnStatus);
    backend.lightBurnResult.connect(onLightBurnResult);
    backend.setLanguage(language);
  });
}

if (location.protocol === "file:" && window.qt && qt.webChannelTransport) {
  const channelScript = document.createElement("script");
  channelScript.src = "qrc:///qtwebchannel/qwebchannel.js";
  channelScript.onload = connectQtBackend;
  channelScript.onerror = () => showError("Nie udało się uruchomić kanału komunikacji Qt.");
  document.head.appendChild(channelScript);
} else {
  $("statusPill").querySelector("b").textContent = translateValue("Podgląd UI");
}

function showView(view) {
  [sourceView, workspaceView, resultView].forEach((item) => item.classList.toggle("active-view", item === view));
}

window.setDropActive = (active) => $("dropZone").classList.toggle("drag", active);

$("dropZone").addEventListener("click", () => backend && backend.chooseInput());
$("folderButton").addEventListener("click", () => backend && backend.chooseFolder());
$("changeProject").addEventListener("click", () => backend && backend.chooseInput());
$("openOutput").addEventListener("click", () => backend && backend.openOutput());
$("openReport").addEventListener("click", () => backend && backend.openReport());
$("loadTop").addEventListener("click", () => backend && backend.loadGeneratedInLightBurn("top"));
$("loadBottom").addEventListener("click", () => backend && backend.loadGeneratedInLightBurn("bottom"));
$("backToProject").addEventListener("click", () => showView(workspaceView));

function onAnalysis(payload) {
  analysis = JSON.parse(payload);
  $("projectName").textContent = analysis.source;
  $("boardSize").textContent = `${analysis.board.width.toFixed(2)} × ${analysis.board.height.toFixed(2)}`;
  $("viaCount").textContent = analysis.drills.vias;
  $("drillDetail").textContent = `${analysis.drills.pth} PTH · ${analysis.drills.npth} NPTH · ${analysis.drills.slots} ${translateValue("slotów")}`;
  $("minFeature").textContent = analysis.minFeatureMm ? `${analysis.minFeatureMm.toFixed(3)} mm` : translateValue("brak danych");
  $("blankWidth").value = analysis.board.width.toFixed(3);
  $("blankHeight").value = analysis.board.height.toFixed(3);
  renderChecks();
  renderLayers();
  selectedPreview = analysis.previews.top ? "top" : Object.keys(analysis.previews)[0];
  renderPreview();
  updatePosition();
  $("generateButton").disabled = !analysis.canGenerate;
  $("exportStatus").textContent = translateValue(analysis.canGenerate ? "Gotowe do wygenerowania" : "Napraw błędy blokujące");
  showView(workspaceView);
  document.querySelectorAll(".step").forEach((step, index) => step.classList.toggle("active", index === 1));
}

function renderChecks() {
  $("checksList").innerHTML = analysis.checks.map((check) => `<div class="check ${check.level}"><i>${check.level === "ok" ? "✓" : check.level === "warning" ? "!" : "×"}</i><div><b>${escapeHtml(translateValue(check.title))}</b><small>${escapeHtml(translateValue(check.detail))}</small></div></div>`).join("");
  $("checkCounter").textContent = analysis.checks.length;
}

function renderLayers() {
  $("layersList").innerHTML = analysis.layers.filter((layer) => layer.kind !== "other").map((layer) => `<div><b>${escapeHtml(layer.kind)}</b> — ${escapeHtml(layer.name)}</div>`).join("");
}

function renderPreview() {
  const source = analysis.previews[selectedPreview];
  $("previewImage").style.display = source ? "block" : "none";
  $("emptyPreview").style.display = source ? "none" : "block";
  if (source) $("previewImage").src = source;
  document.querySelectorAll("[data-preview]").forEach((button) => button.classList.toggle("active", button.dataset.preview === selectedPreview));
}

document.querySelectorAll("[data-preview]").forEach((button) => button.addEventListener("click", () => { selectedPreview = button.dataset.preview; renderPreview(); }));
document.querySelectorAll("input[name=flip]").forEach((input) => input.addEventListener("change", () => {
  document.querySelectorAll(".flip-option").forEach((label) => label.classList.toggle("active", label.contains(document.querySelector("input[name=flip]:checked"))));
}));
["blankWidth", "blankHeight", "originX", "originY"].forEach((id) => $(id).addEventListener("input", updatePosition));

function numeric(id, fallback = 0) {
  const raw = $(id)?.value;
  if (raw == null || String(raw).trim() === "") return fallback;
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}
function updatePosition() {
  if (!analysis) return;
  const x = numeric("originX") + numeric("blankWidth", analysis.board.width) / 2;
  const y = numeric("originY") + numeric("blankHeight", analysis.board.height) / 2;
  $("positionResult").textContent = `X ${x.toFixed(3)} / Y ${y.toFixed(3)} mm`;
}

function collectOptions() {
  const boardWidth = analysis?.board?.width || 0;
  const boardHeight = analysis?.board?.height || 0;
  return {
    dpmm: 50,
    includeGeometry: Boolean(analysis),
    blankWidth: numeric("blankWidth", boardWidth), blankHeight: numeric("blankHeight", boardHeight),
    originX: numeric("originX"), originY: numeric("originY"),
    flip: document.querySelector("input[name=flip]:checked").value,
    speed: numeric("speed", 3000), power: numeric("power", 50), interval: numeric("interval", .05),
    passes: numeric("passes", 2), overscan: numeric("overscan", 2.5),
    boardWidth, boardHeight
  };
}

$("generateButton").addEventListener("click", () => {
  if (!backend || !analysis) return;
  backend.generate(JSON.stringify(collectOptions()));
});

$("applyPreset").addEventListener("click", () => {
  if (!backend) return;
  backend.applyLightBurnPreset(JSON.stringify(collectOptions()));
});

$("openLightBurn").addEventListener("click", () => backend && backend.openLightBurn());

document.querySelectorAll("[data-lb-action]").forEach((button) => button.addEventListener("click", () => {
  if (backend) backend.lightBurnAction(button.dataset.lbAction, false);
}));

$("lbStart").addEventListener("click", () => {
  if (!backend) return;
  if (!$("safetyConfirm").checked) {
    showError(translateValue("Przed Start potwierdź Frame, położenie płytki, wentylację i nadzór."));
    return;
  }
  if (!window.confirm(translateValue("Uruchomić laser? Pozostań przy urządzeniu przez cały proces."))) return;
  backend.lightBurnAction("start", true);
});

function onLightBurnStatus(payload) {
  const status = JSON.parse(payload);
  lastLightBurnStatus = status;
  renderLightBurnStatus(status);
}

function renderLightBurnStatus(status) {
  $("machinePanel").classList.toggle("offline", !status.connected);
  $("lbState").textContent = status.connected ? `${status.ui_status} · ${status.controller}` : translateValue("LightBurn offline");
  $("lbDevice").textContent = status.connected ? status.title : translateValue(status.message);
  $("lbElapsed").textContent = status.elapsed;
  $("lbRemaining").textContent = status.remaining;
  $("lbProgress").style.width = `${Math.max(0, Math.min(1, status.progress)) * 100}%`;
  $("lbPosition").textContent = status.x == null ? "X — / Y —" : `X ${status.x.toFixed(2)} / Y ${status.y.toFixed(2)}`;
  const displayedFeed = status.feed > 0 ? status.feed : status.layer_speed;
  const displayedPower = status.power > 0 ? status.power : status.layer_power;
  $("lbFeed").textContent = displayedFeed == null ? "— mm/min" : `${displayedFeed.toFixed(0)} mm/min`;
  $("lbPower").textContent = displayedPower == null ? "—" : `${displayedPower.toFixed(0)}%`;
  $("lbPasses").textContent = status.layer_passes == null ? "—" : status.layer_passes;
}

function onLightBurnResult(payload) {
  const result = JSON.parse(payload);
  showMessage(translateValue(result.message || "Polecenie wykonane."));
}

function onGenerated(payload) {
  const data = JSON.parse(payload);
  $("outputPath").textContent = data.path;
  showView(resultView);
  document.querySelectorAll(".step").forEach((step, index) => step.classList.toggle("active", index === 3));
}

function setBusy(active, message) {
  $("busyOverlay").classList.toggle("show", active);
  $("busyText").textContent = translateValue(message || "Pracuję…");
  $("statusPill").querySelector("b").textContent = translateValue(active ? "Przetwarzanie" : "Gotowy");
}

function showError(message) {
  const toast = $("toast");
  toast.classList.remove("success");
  toast.textContent = translateValue(message);
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 6500);
}

function showMessage(message) {
  const toast = $("toast");
  toast.classList.add("success");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 5000);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
}

translateDocument();
