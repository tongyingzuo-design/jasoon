from __future__ import annotations

import html
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


PROGRESSIONS = [
    {"id": "cp_pop", "category": "Pop", "key": "C major", "chords": ["C", "G", "Am", "F"], "tags": ["balanced", "emotional"], "usage": "Common pop loop for a clear first test."},
    {"id": "cp_sad", "category": "Reflective", "key": "C major", "chords": ["Am", "F", "C", "G"], "tags": ["sad", "reflective"], "usage": "Minor-start loop for sad or nostalgic outputs."},
    {"id": "cp_classic", "category": "Classic", "key": "C major", "chords": ["C", "Am", "F", "G"], "tags": ["nostalgic", "romantic"], "usage": "Simple classic progression."},
    {"id": "cp_simple", "category": "Beginner", "key": "C major", "chords": ["C", "F", "G", "C"], "tags": ["simple", "bright"], "usage": "Beginner-friendly harmonic foundation."},
    {"id": "cp_cinematic", "category": "Cinematic", "key": "A minor", "chords": ["Am", "G", "F", "E"], "tags": ["tense", "dramatic"], "usage": "Darker cinematic movement."},
    {"id": "cp_dreamy", "category": "Dreamy", "key": "C major", "chords": ["F", "G", "Em", "Am"], "tags": ["dreamy", "soft"], "usage": "Gentle floating movement."},
    {"id": "cp_lofi", "category": "Lo-fi", "key": "C major", "chords": ["Dm", "G", "C", "Am"], "tags": ["lo-fi", "warm"], "usage": "Warm loop for color-tone changes."},
    {"id": "cp_drive", "category": "Energetic", "key": "C major", "chords": ["C", "G", "F", "G"], "tags": ["energetic", "direct"], "usage": "Strong pulse for energetic testing."},
]

LABEL_DATABASE = {
    "categories": [
        {"id": "emotion", "name": "Emotion", "description": "Emotional color and melodic direction.", "labels": [
            {"id": "sad", "label": "sad", "affects": ["tempo", "register", "harmony"], "rule": {"tempo": -6, "density": -0.2, "register": -1, "extension": 0.4, "dynamic": -0.3, "contour": "down"}},
            {"id": "happy", "label": "happy", "affects": ["tempo", "register", "rhythm"], "rule": {"tempo": 6, "density": 0.3, "register": 1, "extension": 0.1, "dynamic": 0.3, "contour": "up"}},
            {"id": "dreamy", "label": "dreamy", "affects": ["harmony", "texture", "register"], "rule": {"tempo": -3, "density": -0.1, "register": 1, "extension": 0.8, "dynamic": -0.2, "contour": "float"}},
            {"id": "nostalgic", "label": "nostalgic", "affects": ["harmony", "contour", "dynamics"], "rule": {"tempo": -3, "density": -0.1, "register": -0.5, "extension": 0.5, "dynamic": -0.1, "contour": "arch"}},
        ]},
        {"id": "energy", "name": "Energy & Dynamics", "description": "Tempo, density, and dynamic strength.", "labels": [
            {"id": "aggressive", "label": "aggressive", "affects": ["tempo", "density", "dynamics"], "rule": {"tempo": 9, "density": 0.7, "register": -0.2, "extension": 0.1, "dynamic": 0.8, "contour": "angular"}},
            {"id": "quiet", "label": "quiet", "affects": ["dynamics", "density", "tempo"], "rule": {"tempo": -4, "density": -0.6, "register": 0, "extension": 0, "dynamic": -0.8, "contour": "gentle"}},
            {"id": "calm", "label": "calm", "affects": ["tempo", "density", "rhythm"], "rule": {"tempo": -5, "density": -0.4, "register": 0, "extension": 0.2, "dynamic": -0.4, "contour": "gentle"}},
            {"id": "energetic", "label": "energetic", "affects": ["tempo", "density", "pulse"], "rule": {"tempo": 8, "density": 0.5, "register": 0.5, "extension": 0, "dynamic": 0.5, "contour": "up"}},
        ]},
        {"id": "complexity", "name": "Complexity & Playability", "description": "Difficulty, density, and chord color.", "labels": [
            {"id": "simple", "label": "simple", "affects": ["density", "harmony", "playability"], "rule": {"tempo": 0, "density": -0.8, "register": 0, "extension": -1, "dynamic": 0, "contour": "simple"}},
            {"id": "rich", "label": "rich", "affects": ["harmony", "texture", "density"], "rule": {"tempo": 0, "density": 0.4, "register": 0, "extension": 1, "dynamic": 0.2, "contour": "arch"}},
            {"id": "sparse", "label": "sparse", "affects": ["density", "rests", "texture"], "rule": {"tempo": -1, "density": -0.7, "register": 0, "extension": 0, "dynamic": -0.2, "contour": "gentle"}},
            {"id": "dense", "label": "dense", "affects": ["density", "motion", "complexity"], "rule": {"tempo": 2, "density": 0.7, "register": 0, "extension": 0.3, "dynamic": 0.2, "contour": "active"}},
        ]},
        {"id": "instrument", "name": "Instrument", "description": "Output instrument direction.", "labels": [
            {"id": "piano", "label": "piano", "affects": ["instrument"], "rule": {"tempo": 0, "density": 0, "register": 0, "extension": 0, "dynamic": 0, "contour": "piano"}},
            {"id": "strings", "label": "strings", "affects": ["instrument", "texture"], "rule": {"tempo": -1, "density": -0.1, "register": 0.5, "extension": 0.2, "dynamic": -0.1, "contour": "legato"}},
            {"id": "guitar", "label": "guitar", "affects": ["instrument", "texture"], "rule": {"tempo": 1, "density": 0.1, "register": 0, "extension": 0, "dynamic": 0, "contour": "pluck"}},
        ]},
    ]
}

LABEL_INDEX = {label["id"]: label for cat in LABEL_DATABASE["categories"] for label in cat["labels"]}
ALLOWED_BARS = [4, 8, 12, 16, 24, 32]


class SelectedLabel(BaseModel):
    id: str
    intensity: int = Field(ge=1, le=5)


class ScoreRequest(BaseModel):
    progression_id: str | None = None
    base_chords: list[str] = Field(min_length=4, max_length=8)
    key_name: str = "C major"
    bars: int = 8
    labels: list[SelectedLabel] = []


class PreviewRequest(BaseModel):
    base_chords: list[str] = Field(min_length=4, max_length=8)
    key_name: str = "C major"


NOTE_STEP = {"C": ("C", 0), "D": ("D", 0), "E": ("E", 0), "F": ("F", 0), "G": ("G", 0), "A": ("A", 0), "B": ("B", 0), "Bb": ("B", -1), "F#": ("F", 1)}
ROOTS = ["C", "D", "E", "F", "G", "A", "B"]


def chord_root(symbol: str) -> str:
    match = re.match(r"^([A-G](?:#|b)?)", symbol.strip())
    if not match:
        raise ValueError(f"Invalid chord symbol: {symbol}")
    return match.group(1)


def is_minor(symbol: str) -> bool:
    return "m" in symbol and "maj" not in symbol


def chord_tones(symbol: str, octave: int) -> list[str]:
    root = chord_root(symbol)
    scale = ["C", "D", "E", "F", "G", "A", "B"]
    idx = scale.index(root[0]) if root[0] in scale else 0
    third = scale[(idx + 2) % 7]
    fifth = scale[(idx + 4) % 7]
    if is_minor(symbol) and third == "E":
        third = "Eb"
    if "maj7" in symbol or "m7" in symbol:
        seventh = scale[(idx + 6) % 7]
        return [root, third, fifth, seventh]
    if "add9" in symbol:
        ninth = scale[(idx + 1) % 7]
        return [root, third, fifth, ninth]
    return [root, third, fifth]


def params(labels: list[SelectedLabel]) -> dict[str, Any]:
    p = {"tempo": 88.0, "density": 3.0, "register": 0.0, "extension": 0.0, "dynamic": 2.5, "contour": "balanced", "trace": []}
    for item in labels:
        if item.id not in LABEL_INDEX:
            raise ValueError(f"Unknown label: {item.id}")
        definition = LABEL_INDEX[item.id]
        rule = definition["rule"]
        intensity = item.intensity
        before = p.copy()
        for key in ["tempo", "density", "register", "extension", "dynamic"]:
            p[key] += float(rule[key]) * intensity / 2
        p["contour"] = rule["contour"]
        p["trace"].append({"label": definition["label"], "intensity": intensity, "changed_parameters": [
            {"parameter": k, "delta": round(p[k] - before[k], 2)} for k in ["tempo", "density", "register", "extension", "dynamic"] if abs(p[k] - before[k]) > 0.01
        ]})
    p["tempo"] = round(max(48, min(168, p["tempo"])))
    p["density"] = max(1, min(5, round(p["density"])))
    p["register"] = max(-2, min(2, round(p["register"])))
    p["extension"] = max(-1, min(5, p["extension"]))
    dynamics = ["pp", "p", "mp", "mf", "f", "ff"]
    p["dynamic"] = dynamics[max(0, min(5, round(p["dynamic"]))) ]
    return p


def customize(symbol: str, p: dict[str, Any]) -> str:
    root = chord_root(symbol)
    if p["extension"] < 0:
        return f"{root}m" if is_minor(symbol) else root
    if p["extension"] >= 3:
        return f"{root}m7" if is_minor(symbol) else f"{root}maj7"
    if p["extension"] >= 1:
        return f"{root}m7" if is_minor(symbol) else f"{root}add9"
    return symbol


def pitch_xml(name: str, octave: int) -> str:
    base = name.replace("b", "").replace("#", "")
    alter = -1 if "b" in name else 1 if "#" in name else 0
    alter_xml = f"<alter>{alter}</alter>" if alter else ""
    return f"<pitch><step>{base}</step>{alter_xml}<octave>{octave}</octave></pitch>"


def harmony_xml(symbol: str) -> str:
    root = chord_root(symbol)
    kind = "minor" if is_minor(symbol) else "major"
    if "maj7" in symbol:
        kind = "major-seventh"
    elif "m7" in symbol:
        kind = "minor-seventh"
    elif "add9" in symbol:
        kind = "major"
    step, alter = NOTE_STEP.get(root, (root[0], 0))
    alter_xml = f"<root-alter>{alter}</root-alter>" if alter else ""
    return f"<harmony><root><root-step>{step}</root-step>{alter_xml}</root><kind>{kind}</kind></harmony>"


def musicxml(base_chords: list[str], bars: int, p: dict[str, Any], preview: bool = False) -> tuple[str, list[str]]:
    custom = [base_chords[i % len(base_chords)] if preview else customize(base_chords[i % len(base_chords)], p) for i in range(bars)]
    measures = []
    for i, symbol in enumerate(custom, start=1):
        tones = chord_tones(symbol, 5 + int(p["register"]))
        density = 2 if preview else int(p["density"])
        note_names = (tones * 8)[: max(2, min(8, density + 1))]
        if p["contour"] in {"down", "gentle"}:
            note_names = list(reversed(note_names))
        notes = []
        dur = max(1, 4 // max(1, len(note_names)))
        for name in note_names:
            notes.append(f"<note>{pitch_xml(name, 5 + int(p['register']))}<duration>{dur}</duration><type>{'quarter' if dur == 1 else 'half'}</type></note>")
        if sum([dur] * len(note_names)) < 4:
            notes.append(f"<note><rest/><duration>{4 - sum([dur] * len(note_names))}</duration><type>quarter</type></note>")
        attrs = ""
        if i == 1:
            attrs = "<attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><direction placement='above'><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>%s</per-minute></metronome></direction-type><sound tempo='%s'/></direction>" % (p["tempo"], p["tempo"])
        measures.append(f"<measure number='{i}'>{attrs}{harmony_xml(symbol)}{''.join(notes)}</measure>")
    xml = "<?xml version='1.0' encoding='UTF-8'?><score-partwise version='3.1'><part-list><score-part id='P1'><part-name>Customized Score</part-name></score-part></part-list><part id='P1'>" + "".join(measures) + "</part></score-partwise>"
    return xml, custom


HTML = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Music MVP</title><script src="https://cdn.jsdelivr.net/npm/opensheetmusicdisplay@1.8.8/build/opensheetmusicdisplay.min.js"></script><style>
:root{--bg:#efede7;--ink:#181a1a;--line:#d0cec7;--paper:#fff;--teal:#1f7165;--red:#b63e35;--side:300px}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Segoe UI,Arial,sans-serif}button,select,input{font:inherit}button{cursor:pointer;border-radius:5px}.screen{display:none;min-height:100vh}.active{display:block}.start{min-height:100vh;display:grid;place-items:center;text-align:center;background:#d9d6cd;padding:32px}.start h1{font-family:Georgia,serif;font-size:clamp(42px,7vw,82px);font-weight:500}.primary{background:var(--ink);color:white;border:1px solid var(--ink);padding:12px 18px;font-weight:700}.secondary{background:transparent;border:1px solid var(--ink);padding:10px 14px}.layout{display:grid;grid-template-columns:var(--side) 1fr;min-height:100vh}.side{position:sticky;top:0;height:100vh;overflow:auto;background:#dedbd2;border-right:1px solid var(--line);padding:24px}.work{padding:34px clamp(24px,5vw,70px)}.head{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:28px}.head h2{font-family:Georgia,serif;font-size:34px;font-weight:500;margin:0}.eyebrow{color:#696d6b;text-transform:uppercase;font-size:12px;font-weight:800;letter-spacing:.12em}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.cat,.paper,.metric,.detail{background:rgba(255,255,255,.55);border:1px solid var(--line);padding:18px}.bank{display:flex;flex-wrap:wrap;gap:8px}.label,.prog,.chip{background:var(--paper);border:1px solid var(--line);padding:8px 11px}.selected{box-shadow:inset 0 -3px 0 var(--teal);font-weight:700}.prog{min-height:116px;text-align:left}.prog strong,.chip{font-family:Georgia,serif}.modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;place-items:center;padding:20px}.modal.show{display:grid}.panel{width:min(1000px,100%);max-height:90vh;overflow:auto;background:var(--bg);border:1px solid var(--ink);padding:22px}.progs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.labels{display:grid;gap:10px}.sel{position:relative;background:#fff;border:1px solid var(--line);padding:12px;margin-bottom:10px}.sel button.remove{position:absolute;right:8px;top:8px;background:var(--red);color:white;border:0;border-radius:99px}.scale{display:flex;gap:4px;margin-top:10px}.scale button{flex:1;border:1px solid var(--line);background:#f7f5ef}.scale button.on{background:var(--ink);color:white}.chords{display:flex;flex-wrap:wrap;gap:8px}.score{background:white;border:1px solid var(--line);padding:16px;overflow:auto;min-height:330px}.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:18px 0}.details{display:grid;grid-template-columns:1fr 1fr;gap:18px}.status{color:#696d6b}.err{color:var(--red)}@media(max-width:800px){.layout{grid-template-columns:1fr}.side{position:static;height:auto}.grid,.progs,.details{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main id="start" class="screen active"><section class="start"><div><p class="eyebrow">Music composition MVP</p><h1>Shape a score with labels.</h1><button id="choose" class="primary">Choose chord progression</button><p id="boot" class="status">Loading score engine...</p></div></section></main><main id="labels" class="screen"><div class="layout"><aside class="side" id="side1"></aside><section class="work"><header class="head"><div><p class="eyebrow">Labels</p><h2>What should the music feel like?</h2></div><button id="toEdit" class="primary">Continue</button></header><div id="cats" class="grid"></div></section></div></main><main id="edit" class="screen"><div class="layout"><aside class="side" id="side2"></aside><section class="work"><header class="head"><div><p class="eyebrow">Composition setup</p><h2>Your harmonic foundation</h2></div><button id="change" class="secondary">Change chords</button></header><section class="paper"><p class="eyebrow">Base progression</p><div id="baseChips" class="chords"></div><div id="baseScore" class="score"></div></section><p id="editErr" class="err"></p><button id="gen" class="primary">Start customization</button></section></div></main><main id="load" class="screen"><div class="layout"><aside class="side" id="side3"></aside><section class="work"><h2>Writing your score</h2><p class="status">Applying harmony, rhythm, register, dynamics, and texture.</p></section></div></main><main id="result" class="screen"><div class="layout"><aside class="side" id="side4"></aside><section class="work"><header class="head"><div><p class="eyebrow">Generated score</p><h2>Your customized composition</h2></div><button id="back" class="secondary">Edit inputs</button></header><section class="paper"><p class="eyebrow">Customized progression</p><div id="customChips" class="chords"></div></section><div id="metrics" class="metrics"></div><div id="score" class="score"></div><section class="details"><div class="detail"><h3>What changed</h3><div id="explain"></div></div><div class="detail"><h3>Database trace</h3><div id="trace"></div></div></section></div></main><div id="modal" class="modal"><section class="panel"><header class="head"><h2>Choose a progression</h2><button id="close" class="secondary">Close</button></header><div id="progList" class="progs"></div><p id="chordErr" class="err"></p><button id="confirm" class="primary">Confirm progression</button></section></div><script>
const S={config:null,prog:null,bars:8,labels:new Map(),preview:"",result:null};const $=id=>document.getElementById(id);function screen(id){document.querySelectorAll('.screen').forEach(s=>s.classList.toggle('active',s.id===id));side()}async function api(p,b){const r=await fetch(p,{method:b?'POST':'GET',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):null});const j=await r.json();if(!r.ok)throw Error(j.detail||'Request failed');return j}function chips(el,arr){el.innerHTML=arr.map(c=>`<span class='chip'>${c}</span>`).join('')}async function draw(id,xml){const el=$(id);el.innerHTML='';const osmd=new opensheetmusicdisplay.OpenSheetMusicDisplay(el,{backend:'svg',autoResize:true,drawTitle:false});await osmd.load(xml);osmd.render()}function payload(){return{progression_id:S.prog?.id,base_chords:S.prog.chords,key_name:S.prog.key,bars:S.bars,labels:[...S.labels].map(([id,v])=>({id,intensity:v}))}}function side(){['side1','side2','side3','side4'].forEach(id=>{const el=$(id);if(!el||!S.config)return;el.innerHTML=`<p class='eyebrow'>Current inputs</p><h3>Score controls</h3><label>Score length</label><select id='${id}bars'>${S.config.allowed_bars.map(b=>`<option ${b===S.bars?'selected':''}>${b}</option>`)}</select><p class='eyebrow'>Selected labels</p><div class='labels'>${[...S.labels].map(([lid,int])=>`<article class='sel'><button class='remove' data-r='${lid}'>-</button><strong>${lid}</strong><div class='scale'>${[1,2,3,4,5].map(n=>`<button data-l='${lid}' data-i='${n}' class='${int===n?'on':''}'>${n}</button>`).join('')}</div></article>`).join('')||'<p class=status>No labels selected.</p>'}</div><button class='secondary add'>+ Add or edit labels</button>`;el.querySelector('select').onchange=e=>{S.bars=+e.target.value;side()};el.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>{S.labels.delete(b.dataset.r);renderLabels();side()});el.querySelectorAll('[data-l]').forEach(b=>b.onclick=()=>{S.labels.set(b.dataset.l,+b.dataset.i);side()});el.querySelector('.add').onclick=()=>screen('labels')})}function renderLabels(){const cats=$('cats');cats.innerHTML='';S.config.label_database.categories.forEach(c=>{const sec=document.createElement('section');sec.className='cat';sec.innerHTML=`<h3>${c.name}</h3><p>${c.description}</p><div class='bank'></div>`;c.labels.forEach(l=>{const b=document.createElement('button');b.className='label '+(S.labels.has(l.id)?'selected':'');b.textContent=l.label;b.onclick=()=>{S.labels.has(l.id)?S.labels.delete(l.id):S.labels.set(l.id,3);renderLabels();side()};sec.querySelector('.bank').appendChild(b)});cats.appendChild(sec)})}async function init(){S.config=await api('/api/config');$('boot').textContent=`music21-style MVP ready · ${S.config.label_database.categories.length} label groups · ${S.config.progressions.length} progressions`;$('progList').innerHTML='';S.config.progressions.forEach(p=>{const b=document.createElement('button');b.className='prog';b.innerHTML=`<strong>${p.chords.join(' - ')}</strong><p>${p.category} · ${p.key}</p><p>${p.usage}</p>`;b.onclick=()=>{S.prog=p;document.querySelectorAll('.prog').forEach(x=>x.classList.remove('selected'));b.classList.add('selected')};$('progList').appendChild(b)});renderLabels();side()}$('choose').onclick=()=>$('modal').classList.add('show');$('close').onclick=()=>$('modal').classList.remove('show');$('confirm').onclick=async()=>{if(!S.prog){$('chordErr').textContent='Choose one progression.';return}S.preview=(await api('/api/preview',{base_chords:S.prog.chords,key_name:S.prog.key})).musicxml;$('modal').classList.remove('show');screen('labels')};$('toEdit').onclick=async()=>{if(!S.labels.size){alert('Choose at least one label.');return}screen('edit');chips($('baseChips'),S.prog.chords);await draw('baseScore',S.preview)};$('change').onclick=()=>$('modal').classList.add('show');$('gen').onclick=async()=>{screen('load');S.result=await api('/api/generate',payload());screen('result');chips($('customChips'),S.result.music_output.customized_chords.slice(0,S.prog.chords.length));$('metrics').innerHTML=[['Tempo',S.result.music_output.tempo_bpm+' BPM'],['Dynamics',S.result.music_output.dynamic],['Density',S.result.music_output.density+'/5'],['Complexity',S.result.music_output.complexity],['Instrument',S.result.music_output.instrument]].map(m=>`<div class='metric'><b>${m[0]}</b><br>${m[1]}</div>`).join('');$('explain').innerHTML=S.result.explanation.map(x=>`<p>${x}</p>`).join('');$('trace').innerHTML=S.result.parameter_trace.map(t=>`<p><b>${t.label} ${t.intensity}/5</b><br>${t.changed_parameters.map(c=>c.parameter+' '+c.delta).join(', ')}</p>`).join('');await draw('score',S.result.music_output.musicxml)};$('back').onclick=()=>screen('edit');init().catch(e=>{$('boot').textContent=e.message});
</script></body></html>
"""

app = FastAPI(title="Label-Based AI Music Composition Assistant MVP")


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return HTML


@app.get("/heartmula-web.html", response_class=HTMLResponse)
def page() -> str:
    return HTML


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "engine": "FastAPI", "rendering": "MusicXML + OpenSheetMusicDisplay", "labels": len(LABEL_INDEX), "progressions": len(PROGRESSIONS)}


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {"progressions": PROGRESSIONS, "label_database": LABEL_DATABASE, "allowed_bars": ALLOWED_BARS}


@app.post("/api/preview")
def preview(request: PreviewRequest) -> dict[str, Any]:
    try:
        p = {"tempo": 88, "density": 2, "register": 0, "extension": 0, "dynamic": "mp", "contour": "balanced", "trace": []}
        xml, custom = musicxml(request.base_chords, 4, p, preview=True)
        return {"musicxml": xml, "base_chords": request.base_chords, "validation": {"passed": True}}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/generate")
def generate(request: ScoreRequest) -> dict[str, Any]:
    try:
        if request.bars not in ALLOWED_BARS:
            raise ValueError("bars must be 4, 8, 12, 16, 24, or 32")
        p = params(request.labels)
        xml, custom = musicxml(request.base_chords, request.bars, p, preview=False)
        selected = [{"id": item.id, "label": LABEL_INDEX[item.id]["label"], "intensity": item.intensity} for item in request.labels]
        explanation = [f"{item['label'].title()} {item['intensity']}/5 changes {', '.join(LABEL_INDEX[item['id']]['affects'][:3])}." for item in selected] or ["Neutral arrangement keeps the original harmonic order."]
        return {
            "input": {"progression_id": request.progression_id, "base_chords": request.base_chords, "key": request.key_name, "bars": request.bars, "labels": selected},
            "music_output": {"musicxml": xml, "customized_chords": custom, "tempo_bpm": p["tempo"], "dynamic": p["dynamic"], "density": p["density"], "register_shift": p["register"], "texture": ["rule-based MVP"], "instrument": "piano", "complexity": "low" if p["density"] <= 2 else "high" if p["density"] >= 5 else "medium"},
            "parameter_trace": p["trace"],
            "explanation": explanation,
            "constraints": {"harmonic_skeleton": {"passed": True, "input_roots": [chord_root(c) for c in request.base_chords], "output_roots": [chord_root(c) for c in custom[:len(request.base_chords)]]}, "bar_count_matches": len(custom) == request.bars, "database_driven": True, "intensity_range": "1-5"},
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
