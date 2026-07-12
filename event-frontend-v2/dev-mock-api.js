/* ============================================================================
   DEV-ONLY mock of the VGI simulation API (no dependencies, Node http).
   Lets the redesigned front end be exercised end-to-end without the Python
   OpenDSS backend. Returns data shaped exactly like the real API:
     - /get-options, /lv-network, /lv-network-defaults
     - /simulate  → base64 plot placeholders + CSV strings whose COLUMNS match
       azure_mockup.py, so the front-end pass/fail logic runs against realistic
       input. Scenario used: a mild LV undervoltage breach + transformer warning.
   NOT for production. Run: node dev-mock-api.js   (listens on :8000)
   ========================================================================== */
const http = require("http");
const fs = require("fs");
const path = require("path");

// Serve the real committed topology JSON so the network explorer works in dev.
const TOPOLOGY_DIR = path.join(__dirname, "..", "vgi_api", "vgi_api", "data");
function loadTopology(nId) {
  try {
    return fs.readFileSync(
      path.join(TOPOLOGY_DIR, `network_topology_${nId}.json`),
      "utf8"
    );
  } catch (e) {
    return null;
  }
}

// 1×1 JPEG placeholder so <img> tags render without a real figure.
const TINY_JPEG =
  "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////" +
  "////////////////////////////////////////////////////////wAALCAABAAEB" +
  "AREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEA" +
  "AD8AfwD/2Q==";

// Real urban (1060) LV network ids, so they line up with the committed
// topology JSON the network explorer renders. 1106/1107 are excluded like in
// the real /lv-network: they host the lumped MV solar / FCS demand.
const NETWORK_IDS = [
  1101,
  1102,
  1103,
  1104,
  1105,
  1108,
  1109,
  1110,
  1111,
  1112,
  1113,
  1114
];
const DEFAULT_NETS = [1101, 1105, 1109];

function csv(header, rows) {
  // Mirror _prepare_csv: header line (comma-joined) then float rows.
  return header.join(",") + "\n" + rows.map(r => r.join(",")).join("\n") + "\n";
}

// Evening bump peaking around 18:00 (row 36 of 48 half-hours).
const bump = t => Math.exp(-Math.pow((t - 36) / 6, 2));

function lvComparison() {
  const nets = DEFAULT_NETS;
  const header = [];
  nets.forEach(id =>
    [0, 25, 50, 75, 100].forEach(q =>
      header.push(`${q}% quantile: LV Network: ${id}`)
    )
  );
  const rows = [];
  for (let t = 0; t < 48; t++) {
    const row = [];
    nets.forEach(id => {
      const median = 1.0 - 0.04 * bump(t);
      const deep = id === 1105 ? 0.004 * bump(t) : 0; // 1105 dips lowest → breach
      [0, 25, 50, 75, 100].forEach(q => {
        const spread = 0.03 * ((q - 50) / 50);
        row.push(+(median + spread - (q === 0 ? deep : 0)).toFixed(4));
      });
    });
    rows.push(row);
  }
  return csv(header, rows);
}

function lvUnbalance(evPen) {
  // VUF % per network over 48 half-hours. Clustered EV load raises it toward
  // the evening peak; higher penetration => more unbalance.
  const nets = DEFAULT_NETS;
  const header = nets.map(id => `VUF %: LV Network ${id}`);
  const peak = 0.4 + 1.8 * Math.min(1, Math.max(0, evPen));
  const rows = [];
  for (let t = 0; t < 48; t++) {
    rows.push(
      nets.map((id, i) => +(peak * bump(t) * (0.7 + 0.2 * i) + 0.05).toFixed(4))
    );
  }
  return csv(header, rows);
}

function mvVoltages() {
  const header = [0, 25, 50, 75, 100].map(q => `MV voltage: ${q}% quantile`);
  const rows = [];
  for (let t = 0; t < 48; t++) {
    const median = 1.01 - 0.015 * bump(t);
    rows.push(
      [0, 25, 50, 75, 100].map(
        q => +(median + 0.025 * ((q - 50) / 50)).toFixed(4)
      )
    );
  }
  return csv(header, rows); // stays within 0.94–1.06 → ok
}

function trnPowers() {
  const header = ["Prmy. Sub. Util."].concat(
    DEFAULT_NETS.map((id, i) => `Sdry. Sub. Util.${id} (${500 + i * 100} kVA)`)
  );
  const rows = [];
  for (let t = 0; t < 48; t++) {
    const prim = 45 + 25 * bump(t); // peak ~70
    const sec = DEFAULT_NETS.map((id, i) => {
      const peak = i === 0 ? 87 : 55 + i * 5; // one secondary approaches rating (~87%)
      return +(30 + (peak - 30) * bump(t)).toFixed(2);
    });
    rows.push([+prim.toFixed(2)].concat(sec));
  }
  return csv(header, rows);
}

function primaryLoadings() {
  const header = [
    "F1 (to 100), 5 MVA",
    "F2 (to 200), 5 MVA",
    "F3 (to 300), 4 MVA"
  ];
  const rows = [];
  for (let t = 0; t < 48; t++)
    rows.push([0, 1, 2].map(f => +(40 + (60 - f * 10) * bump(t)).toFixed(2)));
  return csv(header, rows);
}

function send(res, code, body, type) {
  res.writeHead(code, {
    "Content-Type": type || "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "*"
  });
  res.end(body);
}

http
  .createServer((req, res) => {
    const u = new URL(req.url, "http://localhost:8000");
    if (req.method === "OPTIONS") return send(res, 204, "");

    if (u.pathname === "/get-options") {
      const t = u.searchParams.get("option_type") || "";
      const named = {
        "mv-solar-pv": [
          "None",
          "Commercial PV (summer)",
          "Commercial PV (winter)",
          "csv"
        ],
        "mv-fcs": ["None", "FC weekday", "FC weekend", "csv"],
        "lv-smartmeter": ["None", "Smart meter Jan", "Smart meter Jul", "csv"],
        "lv-ev": ["None", "EV weekday", "EV weekend", "csv"],
        "lv-pv": ["None", "PV summer", "PV winter", "csv"],
        "lv-hp": ["None", "Heat pump winter", "csv"]
      };
      return send(res, 200, JSON.stringify(named[t] || ["None", "csv"]));
    }
    if (u.pathname === "/network-topology") {
      const nId = u.searchParams.get("n_id") || "1060";
      const body = loadTopology(nId);
      if (body === null)
        return send(res, 404, JSON.stringify({ detail: "no topology" }));
      // Mirror the real API's serve-time annotation of the lumped MV asset
      // hosts (run_dict0: dgs -> solar farm, fcs -> fast charging).
      const topo = JSON.parse(body);
      const present = ids => ids.filter(n => topo.lv_networks[String(n)]);
      topo.mv_assets = {
        solar_pv: present([1106, 1142]),
        fcs: present([1107, 1143])
      };
      return send(res, 200, JSON.stringify(topo));
    }
    if (u.pathname === "/lv-network")
      return send(res, 200, JSON.stringify({ networks: NETWORK_IDS }));
    if (u.pathname === "/lv-network-defaults")
      return send(res, 200, JSON.stringify({ networks: DEFAULT_NETS }));

    if (u.pathname === "/simulate") {
      // Mimic the real API's convergence reporting: extreme EV penetration
      // pushes the network past what it can support, so some half-hourly
      // solves fail. Lets the non-convergence banner be exercised in dev.
      const evPen = parseFloat(u.searchParams.get("lv_ev_pen") || "0");
      // Networks actually selected for this run, so the per-phase picker lists
      // the same ids the user chose (falls back to the defaults).
      const selectedNets = (u.searchParams.get("lv_list") || "")
        .split(",")
        .map(s => s.trim())
        .filter(Boolean);
      const phaseNets = selectedNets.length ? selectedNets : DEFAULT_NETS.map(String);
      const convergence =
        evPen >= 0.9
          ? {
              n_steps: 48,
              n_failed: 2,
              failed_steps: [37, 38],
              failed_hours: [18.5, 19.0]
            }
          : { n_steps: 48, n_failed: 0, failed_steps: [], failed_hours: [] };
      return send(
        res,
        200,
        JSON.stringify({
          convergence,
          lv_comparison: TINY_JPEG,
          mv_voltages: TINY_JPEG,
          lv_unbalance: TINY_JPEG,
          // One per-phase figure per selected network (keyed by id).
          lv_phase_pngs: phaseNets.reduce((o, id) => {
            o[String(id)] = TINY_JPEG;
            return o;
          }, {}),
          trn_powers: TINY_JPEG,
          pmry_loadings: TINY_JPEG,
          mv_highlevel_clean: TINY_JPEG,
          mv_highlevel: TINY_JPEG,
          profile_options: TINY_JPEG,
          profile_options_dgs: TINY_JPEG,
          profile_options_fcs: TINY_JPEG,
          lv_comparison_data: lvComparison(),
          mv_voltages_data: mvVoltages(),
          lv_unbalance_data: lvUnbalance(evPen),
          trn_powers_data: trnPowers(),
          primary_loadings_data: primaryLoadings()
        })
      );
    }
    return send(res, 404, JSON.stringify({ detail: "not found" }));
  })
  .listen(process.env.PORT || 8000, "127.0.0.1", function() {
    console.log(
      "Mock VGI API listening on http://127.0.0.1:" + this.address().port
    );
  });
