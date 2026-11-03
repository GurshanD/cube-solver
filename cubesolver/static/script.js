// Front end for the cube solver. The server does all the cube logic and sends back
// the stickers after each move as a string like "UUUUUUUUURRR..." (faces in URFDLB order),
// so this file only has to draw them.

const COLORS = { U: "white", R: "red", F: "green", D: "yellow", L: "orange", B: "blue" };

let states = [];   // sticker strings: scrambled cube, then after each solution move
let moves = [];    // solution moves as text, e.g. ["R", "U'", "F2"]
let step = 0;      // how many solution moves have been applied
let playing = false;

const $ = (id) => document.getElementById(id);

// ---------- drawing ----------

function drawCube(state) {
  const size = Number($("size").value);
  const n = size * size;
  const faces = {};
  "URFDLB".split("").forEach((f, i) => { faces[f] = state.slice(i * n, (i + 1) * n); });

  // Layout of the unfolded cube: [face, row, column] in a 3 row x 4 column grid
  const layout = [["U", 1, 2], ["L", 2, 1], ["F", 2, 2], ["R", 2, 3], ["B", 2, 4], ["D", 3, 2]];

  const net = $("net");
  net.className = "net size-" + size;
  net.innerHTML = "";
  for (const [face, row, col] of layout) {
    const div = document.createElement("div");
    div.className = "face";
    div.style.gridRow = row;
    div.style.gridColumn = col;
    div.style.gridTemplateColumns = `repeat(${size}, auto)`;
    for (const sticker of faces[face]) {
      const s = document.createElement("div");
      s.className = "sticker";
      s.style.background = COLORS[sticker];
      div.appendChild(s);
    }
    net.appendChild(div);
  }

  const solved = isSolved(state, n);
  $("status").textContent = solved ? "Solved!" : "Scrambled";
  $("status").className = solved ? "status solved" : "status";
}

function isSolved(state, n) {
  for (let i = 0; i < 6; i++) {
    const face = state.slice(i * n, (i + 1) * n);
    if (face.split("").some((c) => c !== face[0])) return false;
  }
  return true;
}

function drawMoves() {
  $("solution").innerHTML = moves.length
    ? moves.map((m, i) => `<span class="${i === step - 1 ? "current" : ""}">${m}</span>`).join(" ")
    : "(already solved)";
  $("step-label").textContent = moves.length ? `move ${step} of ${moves.length}` : "";
  $("prev").disabled = step === 0;
  $("next").disabled = step >= moves.length;
  $("reset").disabled = step === 0;
}

function goTo(newStep) {
  step = newStep;
  drawCube(states[step]);
  drawMoves();
}

// ---------- talking to the server ----------

async function getJSON(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong (" + res.status + ")");
  }
  return data;
}

async function showScramble() {
  const size = $("size").value;
  const scramble = encodeURIComponent($("scramble").value);
  try {
    const data = await getJSON(`/api/preview?size=${size}&scramble=${scramble}`);
    $("error").textContent = "";
    $("result").hidden = true;
    stopPlaying();
    drawCube(data.state);
  } catch (err) {
    $("error").textContent = err.message;
  }
}

async function solve() {
  $("solve").disabled = true;
  $("solve").textContent = "Searching...";
  $("error").textContent = "";
  stopPlaying();
  try {
    const result = await getJSON("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        size: Number($("size").value),
        scramble: $("scramble").value,
        algorithm: $("algorithm").value,
        seconds: 15,
      }),
    });
    showResult(result);
  } catch (err) {
    $("error").textContent = err.message;
  }
  $("solve").disabled = false;
  $("solve").textContent = "Solve";
}

function showResult(r) {
  $("result").hidden = false;
  $("expanded").textContent = r.expanded.toLocaleString();
  $("stored").textContent = r.stored.toLocaleString();
  $("time").textContent = r.seconds.toFixed(3) + " s";

  if (r.status !== "solved") {
    $("summary").textContent = `${r.name} gave up (${r.note}). Try a shorter scramble or A*.`;
    $("solution").textContent = "-";
    $("length-out").textContent = "-";
    states = r.states;
    moves = [];
    goTo(0);
    $("step-label").textContent = "";
    return;
  }

  $("summary").textContent = r.optimal
    ? `${r.name} found a ${r.length} move solution. This is the shortest possible.`
    : `${r.name} found a ${r.length} move solution. DFS doesn't guarantee it's the shortest.`;
  if (Number($("size").value) === 2) {
    $("summary").textContent += " (A 2x2 has no centers, so it can end up solved but turned.)";
  }
  $("length-out").textContent = r.length;
  states = r.states;
  moves = r.solution ? r.solution.split(" ") : [];
  goTo(0);
}

// ---------- playback ----------

function stopPlaying() {
  playing = false;
  $("play").textContent = "Play";
}

async function play() {
  if (playing) { stopPlaying(); return; }
  if (step >= moves.length) goTo(0);
  playing = true;
  $("play").textContent = "Pause";
  while (playing && step < moves.length) {
    await new Promise((r) => setTimeout(r, 600));
    if (playing) goTo(step + 1);
  }
  stopPlaying();
}

// ---------- buttons ----------

$("solve").onclick = solve;
$("next").onclick = () => goTo(step + 1);
$("prev").onclick = () => goTo(step - 1);
$("reset").onclick = () => { stopPlaying(); goTo(0); };
$("play").onclick = play;

$("random").onclick = async () => {
  const data = await getJSON(`/api/scramble?size=${$("size").value}&length=${$("length").value}`);
  $("scramble").value = data.scramble;
  showScramble();
};

$("size").onchange = () => {
  $("length").value = $("size").value === "2" ? 20 : 6;
  $("random").click();
};

let typingTimer;
$("scramble").oninput = () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(showScramble, 300);
};

// show the loading note until the server's lookup tables are ready
async function checkTables() {
  const data = await getJSON("/api/status");
  $("loading").hidden = data.tables_ready;
  if (!data.tables_ready) setTimeout(checkTables, 1500);
}

checkTables();
showScramble();
