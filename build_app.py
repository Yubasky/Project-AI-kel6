import csv
import json
import re

csv_path = "laptop_data_cleaned (2).csv"
html_path = "rekomendasi_laptop.html"

laptops = []
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # cleaning row
        clean_row = {}
        for k, v in row.items():
            clean_row[k.strip()] = v.strip() if v else ''
        laptops.append(clean_row)

laptops_json = json.dumps(laptops, separators=(',', ':'))

html_template = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistem Pakar Laptop - Fuzzy Logic</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --success: #10b981;
            --danger: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: var(--bg); color: var(--text-main); line-height: 1.5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; display: grid; grid-template-columns: 350px 1fr; gap: 2rem; }
        @media (max-width: 900px) { .container { grid-template-columns: 1fr; } }
        
        /* Header */
        header { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 3rem 2rem; text-align: center; }
        header h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 1rem; }
        header p { color: #cbd5e1; font-size: 1.1rem; max-width: 600px; margin: 0 auto; }
        
        /* Form Card */
        .glass-card { background: var(--card-bg); border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1); border: 1px solid var(--border); }
        .form-group { margin-bottom: 1.5rem; }
        .form-group label { display: block; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-main); font-size: 0.9rem; }
        .form-control { width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 8px; font-size: 0.95rem; outline: none; transition: border-color 0.2s; background: #fff; }
        .form-control:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
        
        /* Range Slider */
        .budget-display { display: block; font-size: 1.25rem; font-weight: 700; color: var(--primary); margin-bottom: 0.5rem; }
        input[type=range] { width: 100%; accent-color: var(--primary); }
        .range-labels { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }
        
        /* Button */
        .btn { display: inline-block; width: 100%; padding: 1rem; background: var(--primary); color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        .btn:hover { background: var(--primary-hover); }
        
        /* Results Area */
        .results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
        .results-header h2 { font-size: 1.5rem; font-weight: 700; }
        .badge { background: #dbeafe; color: #1e40af; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.875rem; font-weight: 600; }
        
        .grid-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem; }
        
        /* Laptop Card */
        .card { background: var(--card-bg); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: relative; transition: transform 0.2s, box-shadow 0.2s; cursor: pointer;}
        .card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
        
        .card-header { padding: 1.5rem 1.5rem 0.5rem; border-bottom: 1px solid var(--border); }
        .card-brand { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: var(--primary); letter-spacing: 0.05em; margin-bottom: 0.25rem; }
        .card-title { font-size: 1.1rem; font-weight: 600; color: var(--text-main); margin-bottom: 0.5rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .card-price { font-size: 1.25rem; font-weight: 700; color: var(--success); }
        
        .card-body { padding: 1rem 1.5rem; }
        .spec-item { display: flex; align-items: center; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem; }
        .spec-item svg { width: 16px; height: 16px; margin-right: 0.5rem; fill: currentColor; }
        
        /* Score Badge inside Card */
        .score-badge { position: absolute; top: 1rem; right: 1rem; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.9rem; color: white; background: conic-gradient(var(--primary) var(--pct), #e2e8f0 0); }
        .score-badge::after { content: attr(data-score); position: absolute; width: 40px; height: 40px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--text-main); }
        
        .card-footer { padding: 1rem 1.5rem; background: #f8fafc; text-align: center; border-top: 1px solid var(--border); font-size: 0.9rem; font-weight: 600; color: var(--primary); }
        
        .empty-state { text-align: center; padding: 4rem 2rem; background: white; border-radius: 12px; border: 1px dashed var(--border); grid-column: 1 / -1; }
        .empty-state h3 { font-size: 1.25rem; margin-bottom: 0.5rem; color: var(--text-main); }
        .empty-state p { color: var(--text-muted); }
        
        /* Modal */
        .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 50; align-items: center; justify-content: center; padding: 1rem; }
        .modal.active { display: flex; }
        .modal-content { background: white; border-radius: 16px; width: 100%; max-width: 600px; max-height: 90vh; overflow-y: auto; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); position: relative;}
        .modal-header { padding: 1.5rem; border-bottom: 1px solid var(--border); }
        .modal-close { position: absolute; top: 1.5rem; right: 1.5rem; background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-muted); line-height: 1;}
        .modal-body { padding: 1.5rem; }
        .modal-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; padding-right: 2rem;}
        .spec-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.5rem; }
        .spec-box { background: var(--bg); padding: 1rem; border-radius: 8px; border: 1px solid var(--border); }
        .spec-box-label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600; margin-bottom: 0.25rem; }
        .spec-box-val { font-weight: 500; font-size: 0.95rem; }
    </style>
</head>
<body>

<header>
    <h1>💻 Sistem Rekomendasi Laptop</h1>
    <p>Sistem Pakar Berbasis Fuzzy Logic (Sugeno & Tsukamoto) untuk Membantu Memilih Laptop Ideal Berdasarkan Kebutuhan Akademik</p>
</header>

<div class="container">
    <!-- Sidebar Form -->
    <aside class="glass-card">
        <form id="filterForm">
            
            <div class="form-group">
                <label>Metode Fuzzy</label>
                <select id="methodSelect" class="form-control">
                    <option value="sugeno">Fuzzy Sugeno (Orde Nol)</option>
                    <option value="tsukamoto">Fuzzy Tsukamoto</option>
                </select>
            </div>

            <div class="form-group">
                <label>Maksimal Budget</label>
                <div class="budget-display" id="budgetDisplay">Rp 15.000.000</div>
                <input type="range" id="budgetSlider" min="2000000" max="40000000" step="500000" value="15000000">
                <div class="range-labels">
                    <span>2 Jt</span>
                    <span>40 Jt</span>
                </div>
            </div>

            <div class="form-group">
                <label>Profil Akademik</label>
                <select id="profileSelect" class="form-control">
                    <option value="Administrasi">📝 Administrasi / Tugas Umum</option>
                    <option value="Pemrograman">💻 Pemrograman / Data Science</option>
                    <option value="Desain">🎨 Desain Grafis / Multimedia</option>
                    <option value="Gaming">🎮 Gaming / Kinerja Tinggi</option>
                </select>
            </div>

            <div class="form-group">
                <label>Brand (Opsional)</label>
                <select id="brandSelect" class="form-control">
                    <option value="Semua">Semua Brand</option>
                    <option value="Razer">Razer</option>
                    <option value="MSI">MSI</option>
                    <option value="Microsoft">Microsoft</option>
                    <option value="Lenovo">Lenovo</option>
                    <option value="HP">HP</option>
                    <option value="Dell">Dell</option>
                    <option value="Axioo">Axioo</option>
                    <option value="Asus">Asus</option>
                    <option value="Acer">Acer</option>
                </select>
            </div>

            <div class="form-group">
                <label>Sistem Operasi (Opsional)</label>
                <select id="osSelect" class="form-control">
                    <option value="Semua">Semua OS</option>
                    <option value="Windows 11">Windows 11</option>
                    <option value="Windows 10">Windows 10</option>
                </select>
            </div>

            <div class="form-group">
                <label>Ukuran Layar Minimal (Opsional)</label>
                <select id="displaySelect" class="form-control">
                    <option value="0">Tidak ada preferensi</option>
                    <option value="13">≥ 13"</option>
                    <option value="14">≥ 14"</option>
                    <option value="15.6">≥ 15.6"</option>
                </select>
            </div>

            <button type="submit" class="btn">Cari Rekomendasi</button>
        </form>
    </aside>

    <!-- Main Content -->
    <main>
        <div class="results-header">
            <h2>Rekomendasi Teratas</h2>
            <span class="badge" id="resultCount">0 Laptop Ditemukan</span>
        </div>
        <div class="grid-cards" id="resultsGrid">
            <div class="empty-state">
                <h3>Silakan tekan "Cari Rekomendasi"</h3>
                <p>Atur kriteria di samping untuk melihat laptop terbaik yang sesuai.</p>
            </div>
        </div>
    </main>
</div>

<!-- Modal -->
<div class="modal" id="detailModal">
    <div class="modal-content">
        <button class="modal-close" id="closeModal">&times;</button>
        <div class="modal-header">
            <div class="card-brand" id="modalBrand">BRAND</div>
            <h3 class="modal-title" id="modalName">Laptop Name</h3>
            <div class="card-price" id="modalPrice">Rp 10.000.000</div>
        </div>
        <div class="modal-body">
            <div style="background: #eff6ff; padding: 1rem; border-radius: 8px; border: 1px solid #bfdbfe; margin-bottom: 1rem;">
                <h4 style="color: #1e40af; font-size: 0.9rem; margin-bottom: 0.25rem;">Skor Fuzzy Logic: <span id="modalScoreText" style="font-weight: 700; font-size: 1.1rem;">95</span>/100</h4>
                <p style="font-size: 0.85rem; color: #1e3a8a; margin-top:0.5rem;" id="modalReason">Alasan...</p>
            </div>

            <div class="spec-grid">
                <div class="spec-box"><div class="spec-box-label">Processor</div><div class="spec-box-val" id="modalCPU"></div></div>
                <div class="spec-box"><div class="spec-box-label">Graphics (VGA)</div><div class="spec-box-val" id="modalGPU"></div></div>
                <div class="spec-box"><div class="spec-box-label">RAM</div><div class="spec-box-val" id="modalRAM"></div></div>
                <div class="spec-box"><div class="spec-box-label">Penyimpanan</div><div class="spec-box-val" id="modalStorage"></div></div>
                <div class="spec-box"><div class="spec-box-label">Ukuran Layar</div><div class="spec-box-val" id="modalDisplay"></div></div>
                <div class="spec-box"><div class="spec-box-label">Tipe Layar</div><div class="spec-box-val" id="modalDisplayType"></div></div>
                <div class="spec-box"><div class="spec-box-label">Sistem Operasi</div><div class="spec-box-val" id="modalOS"></div></div>
                <div class="spec-box"><div class="spec-box-label">Berat</div><div class="spec-box-val" id="modalWeight"></div></div>
            </div>
        </div>
    </div>
</div>

<script>
// ==========================================
// 1. DATASET RIIL (Dimasukkan via Script)
// ==========================================
const dataset = __DATASET__;

// ==========================================
// 2. PARSER & HELPERS
// ==========================================
const formatRp = (num) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(num);

function parsePrice(priceStr) {
    if (!priceStr) return 0;
    const clean = priceStr.replace(/[^0-9]/g, '');
    return clean ? parseInt(clean) : 0;
}

function parseRAM(ramStr) {
    if (!ramStr) return 4;
    const clean = ramStr.replace(/[^0-9]/g, '');
    return clean ? parseInt(clean) : 4;
}

function parseStorage(storageStr) {
    if (!storageStr) return 256;
    let val = parseInt(storageStr.replace(/[^0-9]/g, ''));
    if (!val) return 256;
    if (storageStr.toUpperCase().includes('TB')) val *= 1024;
    return val;
}

function parseDisplay(displayStr) {
    if (!displayStr) return 14.0;
    const match = displayStr.replace(',', '.').match(/[0-9.]+/);
    return match ? parseFloat(match[0]) : 14.0;
}

// ==========================================
// 3. FUZZY LOGIC SCORES mapping
// ==========================================
function getCPUScore(cpuStr) {
    const s = cpuStr.toLowerCase();
    
    // Default fallback
    let score = 30; 
    
    // Intel
    if (s.includes('i9')) score = 95;
    else if (s.includes('i7')) {
        score = (s.match(/12\d{3}|13\d{3}/)) ? 80 : 60;
    }
    else if (s.includes('i5')) {
        score = (s.match(/12\d{3}|13\d{3}/)) ? 65 : 40;
    }
    else if (s.includes('i3')) {
        score = (s.match(/12\d{3}|13\d{3}/)) ? 35 : 25;
    }
    else if (s.includes('celeron') || s.includes('pentium')) score = 10;
    
    // AMD
    else if (s.includes('ryzen 9')) score = 95;
    else if (s.includes('ryzen 7')) {
        score = (s.match(/6\d{3}|7\d{3}/)) ? 80 : 65;
    }
    else if (s.includes('ryzen 5')) {
        score = (s.match(/6\d{3}|7\d{3}/)) ? 65 : 45;
    }
    else if (s.includes('ryzen 3')) score = 30;

    return score;
}

function getGPUScore(vgaStr) {
    const s = vgaStr.toLowerCase();
    if (s.includes('3070') || s.includes('3080') || s.match(/4070|4080|4090/) || s.match(/rx 6800|rx 6900|rx 7800|rx 7900/)) return 95; // High
    if (s.includes('3060') || s.match(/4050|4060/) || s.match(/rx 6600|rx 6700|rx 7600/)) return 70; // Mid
    if (s.includes('mx') || s.includes('1650') || s.includes('2050') || s.includes('3050')) return 40; // Entry
    return 15; // Integrated
}

// ==========================================
// 4. FUZZY MEMBERSHIP FUNCTIONS
// ==========================================
function trapesium(x, a, b, c, d) {
    if (x <= a || x >= d) return 0;
    if (x > a && x < b) return (x - a) / (b - a);
    if (x >= b && x <= c) return 1;
    if (x > c && x < d) return (d - x) / (d - c);
    return 0;
}

function segitiga(x, a, b, c) {
    if (x <= a || x >= c) return 0;
    if (x > a && x <= b) return (x - a) / (b - a);
    if (x > b && x < c) return (c - x) / (c - b);
    return 0;
}

function evaluateRules(cpu, gpu, ram, storage, ratio) {
    // Fuzzification
    const f_cpu = {
        rendah: trapesium(cpu, 0, 0, 30, 50),
        sedang: segitiga(cpu, 30, 60, 80),
        tinggi: trapesium(cpu, 60, 100, 100, 100)
    };
    const f_gpu = {
        integrated: trapesium(gpu, 0, 0, 15, 35),
        entry: segitiga(gpu, 20, 40, 60),
        mid: segitiga(gpu, 50, 70, 85),
        high: trapesium(gpu, 75, 95, 100, 100)
    };
    const f_ram = {
        kecil: trapesium(ram, 0, 0, 4, 8),
        cukup: segitiga(ram, 4, 16, 32),
        besar: trapesium(ram, 16, 32, 64, 64)
    };
    const f_stor = {
        kecil: trapesium(storage, 0, 0, 128, 256),
        cukup: segitiga(storage, 128, 512, 1024),
        besar: trapesium(storage, 512, 1024, 4096, 4096)
    };
    const f_harga = {
        mahal: segitiga(ratio, 0, 0, 0.5),
        normal: segitiga(ratio, 0.3, 0.65, 0.9),
        murah: segitiga(ratio, 0.7, 1, 1)
    };

    // 17 Rules Evaluation (Sugeno Orde Nol)
    const rules = [
        { a: Math.min(f_cpu.tinggi, f_gpu.high, f_ram.besar, f_stor.besar), z: 98 },
        { a: Math.min(f_cpu.tinggi, f_gpu.mid, f_ram.besar), z: 85 },
        { a: Math.min(f_cpu.sedang, f_gpu.entry, f_ram.cukup), z: 65 },
        { a: Math.min(f_cpu.sedang, f_gpu.integrated, f_ram.cukup), z: 50 },
        { a: Math.min(f_cpu.rendah, f_gpu.integrated, f_ram.kecil), z: 30 },
        { a: f_harga.murah, z: 100 },
        { a: f_harga.normal, z: 70 },
        { a: f_harga.mahal, z: 40 },
        { a: Math.min(f_cpu.tinggi, f_gpu.high, f_harga.mahal), z: 90 },
        { a: Math.min(f_cpu.sedang, f_gpu.entry, f_harga.murah), z: 75 },
        { a: Math.min(f_ram.besar, f_stor.besar, f_gpu.mid), z: 80 },
        { a: Math.min(f_ram.kecil, f_gpu.integrated), z: 20 },
        { a: Math.min(f_cpu.tinggi, f_ram.cukup, f_gpu.integrated), z: 55 },
        { a: Math.min(f_harga.murah, f_cpu.sedang, f_gpu.entry), z: 80 },
        { a: Math.min(f_harga.mahal, f_gpu.high, f_ram.besar), z: 95 },
        { a: Math.min(f_cpu.tinggi, f_gpu.entry), z: 60 },
        { a: Math.min(f_stor.besar, f_harga.murah), z: 85 },
    ];

    let sumAZ = 0, sumA = 0;
    rules.forEach(r => {
        sumAZ += r.a * r.z;
        sumA += r.a;
    });

    if (sumA === 0) return 30; // base score if no rules fire
    return sumAZ / sumA;
}

// ==========================================
// 5. MAIN LOGIC (PRE-FILTER & SCORING)
// ==========================================
document.getElementById('budgetSlider').addEventListener('input', function(e) {
    document.getElementById('budgetDisplay').textContent = formatRp(e.target.value);
});

document.getElementById('filterForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const budget = parseInt(document.getElementById('budgetSlider').value);
    const profile = document.getElementById('profileSelect').value;
    const brandPref = document.getElementById('brandSelect').value;
    const osPref = document.getElementById('osSelect').value;
    const minDisplay = parseFloat(document.getElementById('displaySelect').value);
    
    let filtered = [];
    
    dataset.forEach(laptop => {
        const price = parsePrice(laptop.Harga);
        const ram = parseRAM(laptop.RAM);
        const storage = parseStorage(laptop.Penyimpanan);
        const display = parseDisplay(laptop["Ukuran Layar"]);
        
        const cpuStr = laptop.Processor.toLowerCase();
        const gpuStr = laptop.VGA.toLowerCase();
        
        // 1. HARD FILTERS
        if (price === 0 || price > budget) return;
        if (brandPref !== "Semua" && laptop.Brand !== brandPref) return;
        if (osPref !== "Semua" && !laptop["Sistem Operasi"].includes(osPref)) return;
        if (minDisplay > 0 && display < minDisplay) return;
        
        // Profile Hard Filters
        if (profile === "Pemrograman") {
            if (cpuStr.includes('i3') || cpuStr.includes('celeron') || cpuStr.includes('pentium') || cpuStr.includes('ryzen 3')) return; // Require i5/R5+
            if (ram < 8 || storage < 256) return;
        } 
        else if (profile === "Desain") {
            if (!cpuStr.includes('i7') && !cpuStr.includes('i9') && !cpuStr.includes('ryzen 7') && !cpuStr.includes('ryzen 9')) return;
            if (ram < 16 || storage < 512) return;
            // Require dedicated GPU
            if (gpuStr.includes('integrated') || gpuStr.includes('graphics') || gpuStr.includes('uhd') || gpuStr.includes('iris') || gpuStr === "amd radeon") {
                // strict check for dedicated GPU
                if (!gpuStr.includes('nvidia') && !gpuStr.includes('rtx') && !gpuStr.includes('gtx') && !gpuStr.includes('rx 6') && !gpuStr.includes('rx 7')) return;
            }
        }
        else if (profile === "Gaming") {
            if (!cpuStr.includes('i7') && !cpuStr.includes('i9') && !cpuStr.includes('ryzen 7') && !cpuStr.includes('ryzen 9')) return;
            if (ram < 16 || storage < 512) return;
            // Require Mid/High Dedicated GPU
            const gpuS = getGPUScore(laptop.VGA);
            if (gpuS < 70) return; // Must be at least mid tier
        }
        else if (profile === "Administrasi") {
            if (cpuStr.includes('celeron') || cpuStr.includes('pentium')) return; // min i3/r3
            if (ram < 4 || storage < 256) return;
        }

        // 2. SCORING
        const cpuScore = getCPUScore(laptop.Processor);
        const gpuScore = getGPUScore(laptop.VGA);
        const ratio = Math.min(1, budget / price);
        
        let finalScore = evaluateRules(cpuScore, gpuScore, ram, storage, ratio);
        
        filtered.push({
            ...laptop,
            _price: price,
            _score: finalScore
        });
    });
    
    // Sort and get top 10
    filtered.sort((a, b) => b._score - a._score);
    const top10 = filtered.slice(0, 10);
    
    renderResults(top10);
});

// ==========================================
// 6. RENDER UI
// ==========================================
function renderResults(laptops) {
    const grid = document.getElementById('resultsGrid');
    document.getElementById('resultCount').textContent = `${laptops.length} Laptop Ditemukan`;
    
    if (laptops.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <svg style="width:48px;height:48px;color:#cbd5e1;margin-bottom:1rem;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <h3>Tidak ada laptop yang memenuhi kriteria</h3>
                <p>Silakan perlonggar profil akademik atau naikkan budget Anda.</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = '';
    laptops.forEach(laptop => {
        const s = Math.round(laptop._score);
        const pct = s + '%';
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="score-badge" style="--pct: ${pct}" data-score="${s}"></div>
            <div class="card-header">
                <div class="card-brand">${laptop.Brand}</div>
                <div class="card-title" title="${laptop.Nama}">${laptop.Nama}</div>
                <div class="card-price">${formatRp(laptop._price)}</div>
            </div>
            <div class="card-body">
                <div class="spec-item"><svg viewBox="0 0 24 24"><path d="M9 3H15V5H9V3ZM5 9H3V15H5V9ZM19 9H21V15H19V9ZM9 19H15V21H9V19ZM7 5H5V7H7V5ZM19 5H17V7H19V5ZM7 17H5V19H7V17ZM19 17H17V19H19V17ZM17 7H7V17H17V7ZM15 9H9V15H15V9Z"/></svg> ${laptop.Processor}</div>
                <div class="spec-item"><svg viewBox="0 0 24 24"><path d="M2 4C2 2.89543 2.89543 2 4 2H20C21.1046 2 22 2.89543 22 4V20C22 21.1046 21.1046 22 20 22H4C2.89543 22 2 21.1046 2 20V4ZM4 4V20H20V4H4ZM6 6H18V18H6V6ZM8 8H16V16H8V8Z"/></svg> ${laptop.VGA}</div>
                <div class="spec-item"><svg viewBox="0 0 24 24"><path d="M4 6C4 4.89543 4.89543 4 6 4H18C19.1046 4 20 4.89543 20 6V18C20 19.1046 19.1046 20 18 20H6C4.89543 20 4 19.1046 4 18V6ZM6 6V18H18V6H6ZM8 8H10V11H8V8ZM14 8H16V11H14V8ZM8 13H10V16H8V13ZM14 13H16V16H14V13Z"/></svg> ${laptop.RAM} | ${laptop.Penyimpanan}</div>
            </div>
            <div class="card-footer">Lihat Detail</div>
        `;
        card.addEventListener('click', () => openModal(laptop));
        grid.appendChild(card);
    });
}

const modal = document.getElementById('detailModal');
document.getElementById('closeModal').onclick = () => modal.classList.remove('active');
modal.onclick = (e) => { if(e.target === modal) modal.classList.remove('active'); };

function openModal(laptop) {
    document.getElementById('modalBrand').textContent = laptop.Brand;
    document.getElementById('modalName').textContent = laptop.Nama;
    document.getElementById('modalPrice').textContent = formatRp(laptop._price);
    document.getElementById('modalScoreText').textContent = Math.round(laptop._score);
    
    document.getElementById('modalCPU').textContent = laptop.Processor;
    document.getElementById('modalGPU').textContent = laptop.VGA;
    document.getElementById('modalRAM').textContent = laptop.RAM;
    document.getElementById('modalStorage').textContent = laptop.Penyimpanan;
    document.getElementById('modalDisplay').textContent = laptop["Ukuran Layar"];
    document.getElementById('modalDisplayType').textContent = laptop["Tipe Layar"];
    document.getElementById('modalOS').textContent = laptop["Sistem Operasi"];
    document.getElementById('modalWeight').textContent = laptop.Berat || "-";
    
    let reason = "Laptop ini dinilai berdasarkan kecocokan harga terhadap budget Anda, serta performa kombinasi CPU, GPU, RAM, dan Penyimpanan yang sesuai dengan aturan logika fuzzy.";
    if (laptop._score > 80) reason = "Sangat Direkomendasikan! Komponen laptop ini memiliki performa tinggi yang relevan dengan kebutuhan Anda dan harga yang cukup masuk akal.";
    else if (laptop._score > 60) reason = "Direkomendasikan. Spesifikasinya cukup memadai untuk kebutuhan Anda dengan skor keseimbangan yang baik.";
    document.getElementById('modalReason').textContent = reason;
    
    modal.classList.add('active');
}
</script>
</body>
</html>"""

final_html = html_template.replace("__DATASET__", laptops_json)
with open(html_path, "w", encoding="utf-8") as f:
    f.write(final_html)

print("HTML file created successfully: " + html_path)
