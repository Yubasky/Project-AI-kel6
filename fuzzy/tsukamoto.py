# -*- coding: utf-8 -*-
"""
============================================================
  MESIN INFERENSI FUZZY TSUKAMOTO
  Metode: Output menggunakan fungsi keanggotaan MONOTON
          (naik untuk TINGGI, turun untuk RENDAH)
  Defuzzifikasi: Rata-rata terbobot (Weighted Average)

  Input (via stdin): JSON berisi daftar laptop dengan field:
    - price       (float)  : harga dalam Rupiah
    - ram_gb      (float)  : RAM dalam GB
    - storage_gb  (float)  : penyimpanan dalam GB
    - display_size (float) : ukuran layar dalam inci
    - cpu_score   (float)  : skor CPU (0-100)
    - gpu_class   (float)  : kelas GPU (1-5)
    - budget      (float)  : budget pengguna dalam Rupiah
    - profile     (str)    : profil akademik pengguna

  Output (stdout): JSON hasil skor untuk setiap laptop
============================================================
"""

import sys
import json
import math


# ============================================================
# FUNGSI KEANGGOTAAN INPUT (TRAPESIUM & SEGITIGA)
# ============================================================

def trapz(x, a, b, c, d):
    """Fungsi keanggotaan trapesium."""
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return (x - a) / (b - a)
    if c < x < d:
        return (d - x) / (d - c)
    return 0.0


def trimf(x, a, b, c):
    """Fungsi keanggotaan segitiga."""
    return trapz(x, a, b, b, c)


# ============================================================
# FUNGSI KEANGGOTAAN OUTPUT MONOTON (TSUKAMOTO)
# ============================================================

def z_tinggi(alpha):
    """
    Output TINGGI: Monoton NAIK.
    mu_tinggi(z) = z / 100  =>  z = alpha * 100
    Domain: [0, 100]
    """
    return alpha * 100.0


def z_rendah(alpha):
    """
    Output RENDAH: Monoton TURUN.
    mu_rendah(z) = (100 - z) / 100  =>  z = 100 - alpha * 100
    Domain: [0, 100]
    """
    return 100.0 - (alpha * 100.0)


def z_sedang(alpha):
    """
    Output SEDANG: Monoton NAIK dari 30 ke 70.
    z = 30 + alpha * 40
    """
    return 30.0 + (alpha * 40.0)


# ============================================================
# MESIN INFERENSI TSUKAMOTO
# ============================================================

def inferensi_tsukamoto(laptop, budget, profile):
    """
    Menghitung skor rekomendasi dengan Metode Tsukamoto.
    
    Setiap aturan menghasilkan nilai alpha (derajat kebenaran),
    lalu z dihitung dari INVERS fungsi keanggotaan monoton.
    Defuzzifikasi: z_crisp = Σ(alpha_i * z_i) / Σ(alpha_i)
    """
    price        = laptop['price']
    cpu_score    = laptop['cpu_score']
    gpu_class    = laptop['gpu_class']
    ram          = laptop['ram_gb']
    storage      = laptop['storage_gb']
    display      = laptop['display_size']

    # -----------------------------------------------------------
    # FUZZIFIKASI INPUT
    # -----------------------------------------------------------
    # Variabel Harga
    mu_harga_murah  = trapz(price, 0, 0, 6_000_000, 12_000_000)
    mu_harga_sedang = trimf(price, 8_000_000, 15_000_000, 25_000_000)
    mu_harga_mahal  = trapz(price, 20_000_000, 30_000_000, 1e13, 1e13)

    # Variabel RAM
    mu_ram_kecil    = trapz(ram, 0, 0, 4, 8)
    mu_ram_cukup    = trimf(ram, 4, 8, 16)
    mu_ram_besar    = trapz(ram, 8, 16, 128, 128)

    # Variabel Penyimpanan
    mu_sim_kecil    = trapz(storage, 0, 0, 256, 512)
    mu_sim_cukup    = trimf(storage, 256, 512, 1024)
    mu_sim_besar    = trapz(storage, 512, 1024, 8192, 8192)

    # Variabel Layar
    mu_layar_kecil   = trapz(display, 0, 0, 11, 13)
    mu_layar_standar = trimf(display, 12, 14, 16)
    mu_layar_besar   = trapz(display, 14, 16, 22, 22)

    # Variabel CPU (dipetakan dari cpu_score 0-100)
    mu_cpu_rendah    = trapz(cpu_score, 0, 0, 35, 55)
    mu_cpu_sedang    = trimf(cpu_score, 40, 65, 85)
    mu_cpu_tinggi    = trapz(cpu_score, 70, 85, 100, 100)

    # Variabel GPU (gpu_class 1=integrated s.d. 5=flagship)
    mu_gpu_basic     = trapz(gpu_class, 0, 1, 1, 2.5)
    mu_gpu_mid       = trimf(gpu_class, 2, 3, 4)
    mu_gpu_high      = trapz(gpu_class, 3.5, 4.5, 5.5, 5.5)

    # Kesesuaian Budget (laptop pada sweet-spot 65%-100% dari budget → nilai penuh)
    mu_budget = trapz(price, 0, budget * 0.5, budget, budget * 1.15)

    # -----------------------------------------------------------
    # EVALUASI ATURAN FUZZY (MINIMUM — AND)
    # rules: daftar tuple (alpha, jenis_output)
    # jenis_output: 'TINGGI', 'RENDAH', 'SEDANG'
    # -----------------------------------------------------------
    rules = []

    # ── Aturan UMUM (berlaku semua profil) ──────────────────────
    # R1: Harga MURAH AND RAM BESAR AND Simpan BESAR → TINGGI (Nilai Luar Biasa)
    rules.append((min(mu_harga_murah, mu_ram_besar, mu_sim_besar), 'TINGGI'))

    # R2: Harga MAHAL AND RAM KECIL AND Simpan KECIL → RENDAH (Tidak Worthit)
    rules.append((min(mu_harga_mahal, mu_ram_kecil, mu_sim_kecil), 'RENDAH'))

    # R3: Harga SEDANG AND RAM CUKUP AND Layar STANDAR → SEDANG
    rules.append((min(mu_harga_sedang, mu_ram_cukup, mu_layar_standar), 'SEDANG'))

    # R4: Harga MURAH AND CPU TINGGI → TINGGI
    rules.append((min(mu_harga_murah, mu_cpu_tinggi), 'TINGGI'))

    # R5: Harga MAHAL AND CPU RENDAH → RENDAH
    rules.append((min(mu_harga_mahal, mu_cpu_rendah), 'RENDAH'))

    # R6: RAM BESAR AND Simpan BESAR AND CPU SEDANG → TINGGI
    rules.append((min(mu_ram_besar, mu_sim_besar, mu_cpu_sedang), 'TINGGI'))

    # R7: RAM KECIL AND CPU RENDAH → RENDAH
    rules.append((min(mu_ram_kecil, mu_cpu_rendah), 'RENDAH'))

    # R8: GPU HIGH AND CPU TINGGI AND RAM BESAR → TINGGI
    rules.append((min(mu_gpu_high, mu_cpu_tinggi, mu_ram_besar), 'TINGGI'))

    # ── Aturan SPESIFIK PER PROFIL ───────────────────────────────
    if profile == 'Pemrograman / Data Science':
        # R9: CPU TINGGI AND RAM BESAR → TINGGI
        rules.append((min(mu_cpu_tinggi, mu_ram_besar), 'TINGGI'))
        # R10: CPU RENDAH → RENDAH
        rules.append((mu_cpu_rendah, 'RENDAH'))
        # R11: Simpan BESAR AND RAM BESAR → TINGGI (data science butuh storage)
        rules.append((min(mu_sim_besar, mu_ram_besar), 'TINGGI'))

    elif profile == 'Desain Grafis / Multimedia':
        # R9: GPU HIGH AND CPU TINGGI → TINGGI
        rules.append((min(mu_gpu_high, mu_cpu_tinggi), 'TINGGI'))
        # R10: GPU BASIC → RENDAH
        rules.append((mu_gpu_basic, 'RENDAH'))
        # R11: Layar BESAR AND GPU HIGH → TINGGI
        rules.append((min(mu_layar_besar, mu_gpu_high), 'TINGGI'))

    elif profile == 'Gaming':
        # R9: GPU HIGH AND CPU TINGGI AND RAM BESAR → TINGGI
        rules.append((min(mu_gpu_high, mu_cpu_tinggi, mu_ram_besar), 'TINGGI'))
        # R10: GPU BASIC → RENDAH
        rules.append((mu_gpu_basic, 'RENDAH'))
        # R11: GPU MID AND CPU SEDANG → SEDANG
        rules.append((min(mu_gpu_mid, mu_cpu_sedang), 'SEDANG'))

    else:  # Administrasi / Tugas Umum
        # R9: Harga MURAH AND RAM CUKUP → TINGGI
        rules.append((min(mu_harga_murah, mu_ram_cukup), 'TINGGI'))
        # R10: RAM KECIL → RENDAH
        rules.append((mu_ram_kecil, 'RENDAH'))
        # R11: CPU SEDANG AND RAM CUKUP AND Harga SEDANG → SEDANG
        rules.append((min(mu_cpu_sedang, mu_ram_cukup, mu_harga_sedang), 'SEDANG'))

    # DEFUZZIFIKASI -- RATA-RATA TERBOBOT (TSUKAMOTO)
    # z_i dihitung dari INVERS fungsi keanggotaan monoton
    # z_crisp = SUM(alpha_i * z_i) / SUM(alpha_i)
    pembilang = 0.0
    penyebut = 0.0
    alasan_aturan = []

    for alpha, jenis in rules:
        if alpha > 0.0:
            # Hitung z dari invers fungsi keanggotaan monoton
            if jenis == 'TINGGI':
                z = z_tinggi(alpha)
            elif jenis == 'RENDAH':
                z = z_rendah(alpha)
            else:  # SEDANG
                z = z_sedang(alpha)

            pembilang += alpha * z
            penyebut  += alpha
            alasan_aturan.append(f"α={alpha:.2f} → z={z:.1f} ({jenis})")

    # Kalau tidak ada aturan aktif, nilai default 50
    if penyebut == 0:
        skor_raw = 50.0
    else:
        skor_raw = pembilang / penyebut

    # Kalikan dengan kesesuaian budget (bobot budget)
    skor_final = round(skor_raw * mu_budget, 4)

    # Tentukan label interpretasi
    if skor_final >= 70:
        label = "Sangat Direkomendasikan"
    elif skor_final >= 40:
        label = "Cukup Direkomendasikan"
    else:
        label = "Tidak Direkomendasikan"

    alasan_str = (
        f"[TSUKAMOTO] Defuzzifikasi rata-rata terbobot: "
        f"z_crisp={skor_raw:.2f} x budget_match={mu_budget:.2f} = {skor_final:.2f}. "
        f"Aturan aktif: {'; '.join(alasan_aturan[:3])}."
    )

    return skor_final, alasan_str, label


# ============================================================
# MAIN — Membaca input JSON, menghitung, mencetak output JSON
# ============================================================

def main():
    # Paksa stdout dan stdin menggunakan UTF-8 agar karakter Yunani/Unicode tidak error di Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON decode error: {str(e)}"}))
        sys.exit(1)

    laptops  = payload.get("laptops", [])
    budget   = float(payload.get("budget", 10_000_000))
    profile  = payload.get("profile", "Administrasi / Tugas Umum")

    results = []
    for laptop in laptops:
        try:
            skor, alasan, label = inferensi_tsukamoto(laptop, budget, profile)
            if skor > 3:
                results.append({
                    "nomor"  : laptop.get("nomor", 0),
                    "name"   : laptop.get("Nama", "N/A"),
                    "brand"  : laptop.get("brand", "N/A"),
                    "price"  : laptop.get("price", 0),
                    "cpu"    : laptop.get("Processor", "N/A"),
                    "gpu"    : laptop.get("VGA", "N/A"),
                    "ram"    : f"{int(laptop.get('ram_gb', 0))} GB",
                    "storage": f"{int(laptop.get('storage_gb', 0))} GB",
                    "display": f"{laptop.get('display_size', 0)}\"",
                    "os"     : laptop.get("Sistem Operasi", "N/A"),
                    "score"  : skor,
                    "reason" : alasan,
                    "label"  : label,
                    "method" : "TSUKAMOTO"
                })
        except Exception as e:
            continue  # Lewati laptop yang gagal diproses

    # Urutkan dari skor tertinggi, ambil 12 terbaik
    results.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps(results[:12], ensure_ascii=False))


if __name__ == "__main__":
    main()
