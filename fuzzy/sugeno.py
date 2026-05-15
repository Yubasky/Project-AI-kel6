# -*- coding: utf-8 -*-
"""
============================================================
  MESIN INFERENSI FUZZY SUGENO (Takagi-Sugeno-Kang) ORDE NOL
  Metode: Output berupa KONSTANTA per aturan
  Defuzzifikasi: Weighted Average  z = SUM(wi * zi) / SUM(wi)

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
# KONSTANTA OUTPUT SUGENO ORDE NOL
# Setiap konsekuen aturan adalah sebuah nilai konstanta z
# ============================================================
Z_SANGAT_TINGGI = 100   # Sangat Direkomendasikan
Z_TINGGI        = 85    # Direkomendasikan
Z_SEDANG        = 60    # Cukup
Z_RENDAH        = 30    # Kurang Direkomendasikan
Z_SANGAT_RENDAH = 10    # Tidak Direkomendasikan


# ============================================================
# MESIN INFERENSI SUGENO
# ============================================================

def inferensi_sugeno(laptop, budget, profile):
    """
    Menghitung skor rekomendasi dengan Metode Sugeno Orde Nol.
    
    Konsekuen setiap aturan adalah konstanta (z).
    Defuzzifikasi: z_crisp = SUM(wi * zi) / SUM(wi)
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

    # Kesesuaian Budget (sweet-spot 65%-100% dari budget → nilai penuh)
    mu_budget = trapz(price, 0, budget * 0.5, budget, budget * 1.15)

    # -----------------------------------------------------------
    # DEFINISI ATURAN FUZZY → KONSTANTA OUTPUT (SUGENO ORDE NOL)
    # Format: (bobot / alpha, konstanta_z, deskripsi)
    # -----------------------------------------------------------
    rules = []

    # ── Aturan UMUM ─────────────────────────────────────────────
    # R1: Harga MURAH AND RAM BESAR AND Simpan BESAR → SANGAT TINGGI
    rules.append((min(mu_harga_murah, mu_ram_besar, mu_sim_besar), Z_SANGAT_TINGGI,
                  "Harga terjangkau + RAM & Storage besar = value sangat tinggi."))

    # R2: Harga MAHAL AND RAM KECIL AND Simpan KECIL → SANGAT RENDAH
    rules.append((min(mu_harga_mahal, mu_ram_kecil, mu_sim_kecil), Z_SANGAT_RENDAH,
                  "Harga mahal namun spesifikasi RAM & Storage sangat minim."))

    # R3: Harga SEDANG AND RAM CUKUP AND Layar STANDAR → SEDANG
    rules.append((min(mu_harga_sedang, mu_ram_cukup, mu_layar_standar), Z_SEDANG,
                  "Spesifikasi seimbang dengan harga menengah."))

    # R4: Harga MURAH AND CPU TINGGI → TINGGI
    rules.append((min(mu_harga_murah, mu_cpu_tinggi), Z_TINGGI,
                  "Harga murah dengan prosesor berperforma tinggi — value terbaik."))

    # R5: Harga MAHAL AND CPU RENDAH → RENDAH
    rules.append((min(mu_harga_mahal, mu_cpu_rendah), Z_RENDAH,
                  "Harga premium tapi CPU rendah — tidak worth it."))

    # R6: RAM BESAR AND Simpan BESAR AND CPU SEDANG → TINGGI
    rules.append((min(mu_ram_besar, mu_sim_besar, mu_cpu_sedang), Z_TINGGI,
                  "Kapasitas RAM & Storage besar mendukung produktivitas tinggi."))

    # R7: RAM KECIL AND CPU RENDAH → SANGAT RENDAH
    rules.append((min(mu_ram_kecil, mu_cpu_rendah), Z_SANGAT_RENDAH,
                  "RAM dan CPU sama-sama rendah, kinerja sangat terbatas."))

    # R8: GPU HIGH AND CPU TINGGI AND RAM BESAR → SANGAT TINGGI
    rules.append((min(mu_gpu_high, mu_cpu_tinggi, mu_ram_besar), Z_SANGAT_TINGGI,
                  "Trifecta sempurna: GPU, CPU, dan RAM kelas atas."))

    # ── Aturan SPESIFIK PER PROFIL ───────────────────────────────
    if profile == 'Pemrograman / Data Science':
        # R9: CPU TINGGI AND RAM BESAR → SANGAT TINGGI
        rules.append((min(mu_cpu_tinggi, mu_ram_besar), Z_SANGAT_TINGGI,
                      "[Coding] Spek monster: CPU & RAM terbaik untuk kompilasi & ML."))
        # R10: CPU RENDAH → RENDAH
        rules.append((mu_cpu_rendah, Z_RENDAH,
                      "[Coding] Prosesor kurang bertenaga untuk pengembangan software."))
        # R11: Simpan BESAR AND RAM BESAR → TINGGI (data science butuh storage)
        rules.append((min(mu_sim_besar, mu_ram_besar), Z_TINGGI,
                      "[Coding] Storage & RAM besar mendukung dataset besar dan VM."))

    elif profile == 'Desain Grafis / Multimedia':
        # R9: GPU HIGH AND CPU TINGGI → SANGAT TINGGI
        rules.append((min(mu_gpu_high, mu_cpu_tinggi), Z_SANGAT_TINGGI,
                      "[Desain] Kombinasi GPU & CPU terbaik untuk rendering 3D."))
        # R10: GPU BASIC → SANGAT RENDAH
        rules.append((mu_gpu_basic, Z_SANGAT_RENDAH,
                      "[Desain] GPU Integrated tidak disarankan untuk desain profesional."))
        # R11: Layar BESAR AND GPU HIGH → TINGGI
        rules.append((min(mu_layar_besar, mu_gpu_high), Z_TINGGI,
                      "[Desain] Layar besar + GPU kuat = pengalaman desain yang nyaman."))

    elif profile == 'Gaming':
        # R9: GPU HIGH AND CPU TINGGI AND RAM BESAR → SANGAT TINGGI
        rules.append((min(mu_gpu_high, mu_cpu_tinggi, mu_ram_besar), Z_SANGAT_TINGGI,
                      "[Gaming] Gaming beast: siap libas game AAA di ultra settings."))
        # R10: GPU BASIC → SANGAT RENDAH
        rules.append((mu_gpu_basic, Z_SANGAT_RENDAH,
                      "[Gaming] Bukan laptop gaming: GPU terlalu lemah untuk game modern."))
        # R11: GPU MID AND CPU SEDANG → SEDANG
        rules.append((min(mu_gpu_mid, mu_cpu_sedang), Z_SEDANG,
                      "[Gaming] Mampu menjalankan game populer pada setting medium."))

    else:  # Administrasi / Tugas Umum
        # R9: Harga MURAH AND RAM CUKUP → TINGGI
        rules.append((min(mu_harga_murah, mu_ram_cukup), Z_TINGGI,
                      "[Umum] Pilihan cerdas: harga terjangkau dengan RAM cukup."))
        # R10: RAM KECIL → RENDAH
        rules.append((mu_ram_kecil, Z_RENDAH,
                      "[Umum] RAM 4GB atau kurang akan terasa lambat untuk multitasking."))
        # R11: CPU SEDANG AND RAM CUKUP → SEDANG
        rules.append((min(mu_cpu_sedang, mu_ram_cukup), Z_SEDANG,
                      "[Umum] Spesifikasi standar cocok untuk keperluan umum sehari-hari."))

    # DEFUZZIFIKASI -- WEIGHTED AVERAGE (SUGENO ORDE NOL)
    # z_crisp = SUM(wi * zi) / SUM(wi)
    pembilang = 0.0
    penyebut  = 0.0
    aturan_aktif = []
    best_reason  = "Tidak ada aturan yang aktif."

    for alpha, z_konst, deskripsi in rules:
        if alpha > 0.0:
            pembilang  += alpha * z_konst
            penyebut   += alpha
            aturan_aktif.append((alpha, z_konst, deskripsi))

    if penyebut == 0:
        skor_raw = 50.0
    else:
        skor_raw = pembilang / penyebut

    # Pilih deskripsi aturan dengan alpha tertinggi sebagai "alasan utama"
    if aturan_aktif:
        aturan_aktif.sort(key=lambda x: x[0], reverse=True)
        best_reason = aturan_aktif[0][2]

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
        f"[SUGENO] Weighted Average: z_crisp={skor_raw:.2f} x budget_match={mu_budget:.2f} "
        f"= {skor_final:.2f}. Alasan utama: {best_reason}"
    )

    return skor_final, alasan_str, label


# ============================================================
# MAIN — Membaca input JSON, menghitung, mencetak output JSON
# ============================================================

def main():
    # Paksa stdout dan stdin menggunakan UTF-8 agar tidak error di Windows (cp1252)
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
            skor, alasan, label = inferensi_sugeno(laptop, budget, profile)
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
                    "method" : "SUGENO"
                })
        except Exception:
            continue  # Lewati laptop yang gagal diproses

    # Urutkan dari skor tertinggi, ambil 12 terbaik
    results.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps(results[:12], ensure_ascii=False))


if __name__ == "__main__":
    main()
