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
    # Harga Ratio
    harga_ratio = min(1.0, budget / price) if price > 0 else 0

    # -----------------------------------------------------------
    # FUZZIFIKASI INPUT
    # -----------------------------------------------------------
    mu_harga_mahal  = trimf(harga_ratio, 0, 0, 0.5)
    mu_harga_normal = trimf(harga_ratio, 0.3, 0.65, 0.9)
    mu_harga_murah  = trimf(harga_ratio, 0.7, 1.0, 1.0)

    mu_ram_kecil    = trapz(ram, 0, 0, 4, 8)
    mu_ram_cukup    = trimf(ram, 4, 16, 32)
    mu_ram_besar    = trapz(ram, 16, 32, 64, 64)

    mu_sim_kecil    = trapz(storage, 0, 0, 128, 256)
    mu_sim_cukup    = trimf(storage, 128, 512, 1024)
    mu_sim_besar    = trapz(storage, 512, 1024, 4096, 4096)

    mu_cpu_rendah    = trapz(cpu_score, 0, 0, 30, 50)
    mu_cpu_sedang    = trimf(cpu_score, 30, 60, 80)
    mu_cpu_tinggi    = trapz(cpu_score, 60, 100, 100, 100)

    mu_gpu_integrated = trapz(gpu_class, 0, 0, 15, 35)
    mu_gpu_entry     = trimf(gpu_class, 20, 40, 60)
    mu_gpu_mid       = trimf(gpu_class, 50, 70, 85)
    mu_gpu_high      = trapz(gpu_class, 75, 95, 100, 100)

    # -----------------------------------------------------------
    # DEFINISI ATURAN FUZZY → KONSTANTA OUTPUT (SUGENO ORDE NOL)
    # Format: (bobot / alpha, konstanta_z, deskripsi)
    # -----------------------------------------------------------
    rules = []

    # 17 Aturan yang diwajibkan:
    rules.append((min(mu_cpu_tinggi, mu_gpu_high, mu_ram_besar, mu_sim_besar), 98, "Spek flagship: CPU Tinggi, GPU High, RAM & Storage Besar."))
    rules.append((min(mu_cpu_tinggi, mu_gpu_mid, mu_ram_besar), 85, "Performa gaming/desain mantap (CPU Tinggi, GPU Mid, RAM Besar)."))
    rules.append((min(mu_cpu_sedang, mu_gpu_entry, mu_ram_cukup), 65, "Spesifikasi pas untuk entry-level multimedia."))
    rules.append((min(mu_cpu_sedang, mu_gpu_integrated, mu_ram_cukup), 50, "Cukup untuk produktivitas ringan dan tugas kantor."))
    rules.append((min(mu_cpu_rendah, mu_gpu_integrated, mu_ram_kecil), 30, "Spesifikasi minimalis, tidak disarankan untuk beban berat."))
    rules.append((mu_harga_murah, 100, "Harga jauh di bawah budget Anda (Sangat Murah)."))
    rules.append((mu_harga_normal, 70, "Harga wajar sesuai dengan budget Anda."))
    rules.append((mu_harga_mahal, 40, "Harga mendekati batas atas budget Anda."))
    rules.append((min(mu_cpu_tinggi, mu_gpu_high, mu_harga_mahal), 90, "Spek premium meski harganya mahal."))
    rules.append((min(mu_cpu_sedang, mu_gpu_entry, mu_harga_murah), 75, "Value for money: Spek lumayan dengan harga murah."))
    rules.append((min(mu_ram_besar, mu_sim_besar, mu_gpu_mid), 80, "Kapasitas RAM & Storage memuaskan ditambah GPU menengah."))
    rules.append((min(mu_ram_kecil, mu_gpu_integrated), 20, "Hanya cocok untuk sekadar ngetik (RAM kecil & GPU integrated)."))
    rules.append((min(mu_cpu_tinggi, mu_ram_cukup, mu_gpu_integrated), 55, "Prosesor kencang tapi tertahan oleh ketiadaan GPU dedicated."))
    rules.append((min(mu_harga_murah, mu_cpu_sedang, mu_gpu_entry), 80, "Rekomendasi kuat: spek cukup baik dengan harga sangat bersahabat."))
    rules.append((min(mu_harga_mahal, mu_gpu_high, mu_ram_besar), 95, "Investasi layak: GPU kencang dan RAM besar meski harga maksimal."))
    rules.append((min(mu_cpu_tinggi, mu_gpu_entry), 60, "Kombinasi CPU tinggi namun GPU kurang bertenaga."))
    rules.append((min(mu_sim_besar, mu_harga_murah), 85, "Laptop penyimpanan besar dengan harga terjangkau."))

    # DEFUZZIFIKASI -- WEIGHTED AVERAGE (SUGENO ORDE NOL)
    pembilang = 0.0
    penyebut  = 0.0
    aturan_aktif = []
    best_reason  = "Tidak ada aturan yang aktif secara signifikan."

    for alpha, z_konst, deskripsi in rules:
        if alpha > 0.0:
            pembilang  += alpha * z_konst
            penyebut   += alpha
            aturan_aktif.append((alpha, z_konst, deskripsi))

    if penyebut == 0:
        skor_final = 30.0 # base score
    else:
        skor_final = round(pembilang / penyebut, 4)

    # Tentukan label interpretasi
    if skor_final >= 70:
        label = "Sangat Direkomendasikan"
    elif skor_final >= 50:
        label = "Direkomendasikan"
    else:
        label = "Cukup Direkomendasikan"

    # Pilih deskripsi aturan dengan alpha tertinggi sebagai "alasan utama"
    if aturan_aktif:
        aturan_aktif.sort(key=lambda x: x[0], reverse=True)
        best_reason = aturan_aktif[0][2]

    alasan_str = f"Skor Fuzzy: {skor_final:.1f}/100. Alasan utama: {best_reason}"

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
                    "garansi": laptop.get("Garansi", "-"),
                    "tipe_layar": laptop.get("Tipe Layar", "-"),
                    "keyboard": laptop.get("Keyboard", "-"),
                    "berat"  : laptop.get("Berat", "-"),
                    "dimensi": laptop.get("Dimensi", "-"),
                    "score"  : skor,
                    "reason" : alasan,
                    "label"  : label,
                    "method" : "SUGENO"
                })
        except Exception:
            continue  # Lewati laptop yang gagal diproses

    # Urutkan dari skor tertinggi, ambil 10 terbaik
    results.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps(results[:10], ensure_ascii=False))


if __name__ == "__main__":
    main()
