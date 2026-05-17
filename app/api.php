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
    if (strpos($lower, 'i9') !== false     || strpos($lower, 'ryzen 9') !== false)  return 90;
    if (strpos($lower, 'i7') !== false     || strpos($lower, 'ryzen 7') !== false)  return 75;
    if (strpos($lower, 'i5') !== false     || strpos($lower, 'ryzen 5') !== false)  return 60;
    if (strpos($lower, 'i3') !== false     || strpos($lower, 'ryzen 3') !== false)  return 40;
    if (strpos($lower, 'pentium') !== false|| strpos($lower, 'celeron') !== false)  return 20;
    return 50;
}

/**
 * Memetakan nama VGA ke kelas GPU (1=integrated … 5=flagship)
 */
function gpuClass(string $vga): float {
    $lower = strtolower($vga);
    if (strpos($lower, '4090') !== false || strpos($lower, '4080') !== false
     || strpos($lower, '3090') !== false || strpos($lower, '3080') !== false)    return 5;
    if (strpos($lower, '4070') !== false || strpos($lower, '3070') !== false
     || strpos($lower, '4060') !== false || strpos($lower, '3060') !== false)    return 4;
    if (strpos($lower, '4050') !== false || strpos($lower, '3050') !== false
     || strpos($lower, '2060') !== false || strpos($lower, '1660') !== false
     || strpos($lower, '1650') !== false || strpos($lower, '2050') !== false)    return 3;
    if (strpos($lower, 'mx') !== false   || strpos($lower, 'radeon') !== false
     || strpos($lower, 'vega') !== false || strpos($lower, '1050') !== false)    return 2;
    return 1; // Integrated / tidak diketahui
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
    $gpu_cl      = gpuClass($l['VGA']             ?? '');
    $brand       = trim($l['Brand']               ?? 'N/A');
    $os          = trim($l['Sistem Operasi']      ?? '');

    // --- Filter optional dari pengguna ---
    if (!empty($brandPref) && strcasecmp($brand, $brandPref) !== 0) continue;
    if (!empty($osPref)    && stripos($os, $osPref) === false)       continue;
    if ($minDisplay > 0    && $display < $minDisplay)                continue;
    // Saring: hanya laptop yang harganya dalam jangkauan budget (maks 115%)
    if ($price > $budget * 1.15)                                     continue;
    if ($price <= 0)                                                  continue;

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
