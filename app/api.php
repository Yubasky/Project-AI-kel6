<?php
error_reporting(0);
ini_set('display_errors', 0);
/**
 * ================================================================
 *  Sistem Pakar Rekomendasi Laptop — Fuzzy Logic
 *  Backend API (PHP + XAMPP)
 *
 *  Alur:
 *    1. Terima request JSON dari frontend (JS)
 *    2. Baca & parse dataset CSV
 *    3. Kirim data ke Python (tsukamoto.py ATAU sugeno.py)
 *       via shell_exec + stdin JSON
 *    4. Kembalikan hasil JSON dari Python ke browser
 * ================================================================
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ================================================================
// 1. BACA INPUT JSON DARI FRONTEND
// ================================================================
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    echo json_encode(['error' => 'Request tidak valid. Pastikan Content-Type: application/json.']);
    exit;
}

$budget     = (float)($input['budget']      ?? 10000000);
$profile    = $input['profile']             ?? 'Administrasi / Tugas Umum';
$method     = strtolower($input['method']   ?? 'sugeno');   // 'sugeno' | 'tsukamoto'
$brandPref  = $input['brand']               ?? '';
$osPref     = $input['os']                  ?? '';
$minDisplay = (float)($input['min_display'] ?? 0);

// Pastikan metode valid
if (!in_array($method, ['sugeno', 'tsukamoto'])) {
    $method = 'sugeno';
}

// ================================================================
// 2. BACA DAN PARSE DATASET CSV
// ================================================================
$csvPath = __DIR__ . '/../laptop_data_cleaned_final.csv';

if (!file_exists($csvPath)) {
    echo json_encode(['error' => "File dataset tidak ditemukan: $csvPath"]);
    exit;
}

/**
 * Mengubah string harga "Rp94.799.000" menjadi float 94799000
 */
function parseHarga(string $str): float {
    $clean = preg_replace('/[^\d]/', '', $str);
    return $clean ? (float)$clean : 0.0;
}

/**
 * Mengubah "16GB" → 16, "4GB" → 4
 */
function parseRAM(string $str): float {
    $clean = preg_replace('/[^\d]/', '', $str);
    return $clean ? (float)$clean : 4.0;
}

/**
 * Mengubah "1TB" → 1024, "512GB" → 512
 */
function parsePenyimpanan(string $str): float {
    $upper = strtoupper($str);
    $val   = (float)preg_replace('/[^\d]/', '', $upper);
    if (strpos($upper, 'TB') !== false) {
        $val *= 1024;
    }
    return $val ?: 256.0;
}

/**
 * Mengubah "14 Inch" atau "15.6 Inch" → 14.0 / 15.6
 */
function parseLayar(string $str): float {
    $str = str_replace(',', '.', $str);
    preg_match('/[\d.]+/', $str, $m);
    return isset($m[0]) ? (float)$m[0] : 14.0;
}

/**
 * Memetakan nama Processor ke skor numerik (0–100)
 */
function cpuScore(string $proc): float {
    $lower = strtolower($proc);
    $is_gen12_13 = preg_match('/12\d{3}|13\d{3}/', $lower);
    $is_ryzen_6_7 = preg_match('/6\d{3}|7\d{3}/', $lower);

    if (strpos($lower, 'celeron') !== false || strpos($lower, 'pentium') !== false) return 10;
    if (strpos($lower, 'i9') !== false) return $is_gen12_13 ? 95 : 75;
    if (strpos($lower, 'i7') !== false) return $is_gen12_13 ? 80 : 60;
    if (strpos($lower, 'i5') !== false) return $is_gen12_13 ? 65 : 40;
    if (strpos($lower, 'i3') !== false) return $is_gen12_13 ? 35 : 25;

    if (strpos($lower, 'ryzen 9') !== false) return $is_ryzen_6_7 ? 95 : 75;
    if (strpos($lower, 'ryzen 7') !== false) return $is_ryzen_6_7 ? 80 : 65;
    if (strpos($lower, 'ryzen 5') !== false) return $is_ryzen_6_7 ? 65 : 45;
    if (strpos($lower, 'ryzen 3') !== false) return 30;

    return 30;
}

/**
 * Memetakan nama VGA ke kelas GPU (0-100)
 */
function gpuScore(string $vga): float {
    $lower = strtolower($vga);
    if (preg_match('/3070|3080|4070|4080|4090|rx 6800|rx 6900/', $lower)) return 95;
    if (preg_match('/3060|4050|4060|rx 6600|rx 7600/', $lower)) return 70;
    if (preg_match('/mx|1650|2050|3050/', $lower)) return 40;
    return 15; // Integrated
}

// ── Baca CSV ─────────────────────────────────────────────────────
$handle = fopen($csvPath, 'r');
if (!$handle) {
    echo json_encode(['error' => 'Gagal membuka file CSV.']);
    exit;
}

$header = fgetcsv($handle);
if (!$header) {
    echo json_encode(['error' => 'CSV kosong atau header tidak terbaca.']);
    fclose($handle);
    exit;
}
// Bersihkan BOM UTF-8 jika ada
$header = array_map(function($h) { return trim(str_replace("\xEF\xBB\xBF", '', $h)); }, $header);

$laptops = [];
$nomor   = 1;

while (($row = fgetcsv($handle)) !== false) {
    if (count($row) !== count($header)) continue;

    $l = array_combine($header, $row);

    // --- Parse kolom teks → numerik ---
    $price       = parseHarga($l['Harga']        ?? '0');
    $ram         = parseRAM($l['RAM']             ?? '4GB');
    $storage     = parsePenyimpanan($l['Penyimpanan'] ?? '256GB');
    $display     = parseLayar($l['Ukuran Layar']  ?? '14 Inch');
    $cpu_sc      = cpuScore($l['Processor']       ?? '');
    $gpu_cl      = gpuScore($l['VGA']             ?? '');
    $brand       = trim($l['Brand']               ?? 'N/A');
    $os          = trim($l['Sistem Operasi']      ?? '');

    // --- Filter optional dari pengguna ---
    if (!empty($brandPref) && strcasecmp($brand, $brandPref) !== 0) continue;
    if (!empty($osPref)    && stripos($os, $osPref) === false)       continue;
    if ($minDisplay > 0    && $display < $minDisplay)                continue;
    
    // Saring harga (maks 100% dari budget)
    if ($price > $budget) continue;
    if ($price <= 0) continue;

    // --- Hard Filter Profil Akademik ---
    $cpuStr = strtolower(trim($l['Processor'] ?? ''));
    $gpuStr = strtolower(trim($l['VGA'] ?? ''));
    
    if (strpos($profile, 'Pemrograman') !== false) {
        if (strpos($cpuStr, 'i3') !== false || strpos($cpuStr, 'celeron') !== false || strpos($cpuStr, 'pentium') !== false || strpos($cpuStr, 'ryzen 3') !== false) continue;
        if ($ram < 8 || $storage < 256) continue;
    } 
    elseif (strpos($profile, 'Desain') !== false) {
        if (!preg_match('/i7|i9|ryzen 7|ryzen 9/', $cpuStr)) continue;
        if ($ram < 16 || $storage < 512) continue;
        if (strpos($gpuStr, 'integrated') !== false || strpos($gpuStr, 'graphics') !== false || strpos($gpuStr, 'uhd') !== false || strpos($gpuStr, 'iris') !== false || $gpuStr === 'amd radeon') {
            if (strpos($gpuStr, 'nvidia') === false && strpos($gpuStr, 'rtx') === false && strpos($gpuStr, 'gtx') === false && strpos($gpuStr, 'rx 6') === false && strpos($gpuStr, 'rx 7') === false) continue;
        }
    }
    elseif (strpos($profile, 'Administrasi') !== false) {
        if (strpos($cpuStr, 'celeron') !== false || strpos($cpuStr, 'pentium') !== false) continue;
        if ($ram < 4 || $storage < 256) continue;
    }
    elseif (strpos($profile, 'Gaming') !== false) {
        if (!preg_match('/i7|i9|ryzen 7|ryzen 9/', $cpuStr)) continue;
        if ($ram < 16 || $storage < 512) continue;
        if ($gpu_cl < 70) continue; // mid-high dedicated GPU
    }

    // --- Satukan semua data ke array ---
    $laptops[] = [
        'nomor'        => $nomor++,
        'Nama'         => trim($l['Nama'] ?? 'N/A'),
        'brand'        => $brand,
        'price'        => $price,
        'Processor'    => trim($l['Processor'] ?? 'N/A'),
        'VGA'          => trim($l['VGA']       ?? 'N/A'),
        'Sistem Operasi' => $os,
        'ram_gb'       => $ram,
        'storage_gb'   => $storage,
        'display_size' => $display,
        'cpu_score'    => $cpu_sc,
        'gpu_class'    => $gpu_cl,
        'Garansi'      => trim($l['Garansi'] ?? '-'),
        'Tipe Layar'   => trim($l['Tipe Layar'] ?? '-'),
        'Keyboard'     => trim($l['Keyboard'] ?? '-'),
        'Berat'        => trim($l['Berat'] ?? '-'),
        'Dimensi'      => trim($l['Dimensi'] ?? '-')
    ];
}
fclose($handle);

if (empty($laptops)) {
    echo json_encode([]);
    exit;
}

// ================================================================
// 3. PANGGIL PYTHON SESUAI METODE YANG DIPILIH
// ================================================================
$pyScript = realpath(__DIR__ . "/../fuzzy/{$method}.py");

if (!$pyScript || !file_exists($pyScript)) {
    echo json_encode(['error' => "Script Python tidak ditemukan: fuzzy/{$method}.py"]);
    exit;
}

// Payload JSON yang akan dikirim ke Python via stdin
$payload = json_encode([
    'laptops' => $laptops,
    'budget'  => $budget,
    'profile' => $profile,
], JSON_UNESCAPED_UNICODE);

// Temukan lokasi Python secara otomatis (Windows & Unix)
$pythonExe = 'python'; // default
if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
    $paths = [
        'python',
        'py',
        'C:\\Users\\mygezou\\AppData\\Local\\Microsoft\\WindowsApps\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\python.exe',
        'C:\\Users\\mygezou\\AppData\\Local\\Programs\\Python\\Python313\\python.exe',
        'C:\\Python313\\python.exe'
    ];
    foreach ($paths as $p) {
        $test = @shell_exec(escapeshellarg($p) . " --version 2>&1");
        if ($test && stripos($test, 'Python') !== false) {
            $pythonExe = escapeshellarg($p);
            break;
        }
    }
} else {
    foreach (['python3', 'python', 'py'] as $cmd) {
        $test = @shell_exec("$cmd --version 2>&1");
        if ($test && stripos($test, 'Python') !== false) {
            $pythonExe = escapeshellarg($cmd);
            break;
        }
    }
}

// ── Jalankan Python dengan stdin piping ─────────────────────────
$descriptors = [
    0 => ['pipe', 'r'],  // stdin  → kita tulis payload
    1 => ['pipe', 'w'],  // stdout → kita baca hasilnya
    2 => ['pipe', 'w'],  // stderr → untuk menangkap error Python
];

$pyScriptEscaped = escapeshellarg($pyScript);
$proc = proc_open("$pythonExe $pyScriptEscaped", $descriptors, $pipes);

if (!is_resource($proc)) {
    echo json_encode(['error' => "Gagal menjalankan interpreter Python. Pastikan Python terinstal dan ada di PATH."]);
    exit;
}

// Tulis payload ke stdin Python
fwrite($pipes[0], $payload);
fclose($pipes[0]);

// Baca output (JSON) dari stdout Python
$output = stream_get_contents($pipes[1]);
fclose($pipes[1]);

// Baca pesan error jika ada
$stderr = stream_get_contents($pipes[2]);
fclose($pipes[2]);

$exitCode = proc_close($proc);

// ================================================================
// 4. VALIDASI OUTPUT DAN KEMBALIKAN KE BROWSER
// ================================================================
if ($exitCode !== 0 || empty(trim($output))) {
    echo json_encode([
        'error'  => "Python gagal dijalankan (kode keluar: $exitCode).",
        'detail' => $stderr ?: 'Tidak ada pesan error dari Python.'
    ]);
    exit;
}

$result = json_decode($output, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    echo json_encode([
        'error'  => 'Output Python bukan JSON yang valid.',
        'raw'    => substr($output, 0, 500)
    ]);
    exit;
}

// Kembalikan hasil akhir ke frontend
echo json_encode($result, JSON_UNESCAPED_UNICODE);
