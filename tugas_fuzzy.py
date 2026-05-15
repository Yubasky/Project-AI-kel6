import pandas as pd
import re
import sys
import io

# Paksa output console ke UTF-8 untuk Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# =====================================================================
# 1. PREPROCESSING DATA
# =====================================================================
print("Memuat dan memproses data...")
df = pd.read_csv('laptop_data_cleaned (2).csv')

def parse_harga(x):
    # Hapus "Rp" dan titik, ubah ke integer
    clean = re.sub(r'[^\d]', '', str(x))
    return int(clean) if clean else 0

def parse_ram(x):
    # Ambil angka saja untuk RAM
    clean = re.sub(r'[^\d]', '', str(x))
    return int(clean) if clean else 0

def parse_penyimpanan(x):
    # Ubah penyimpanan ke GB (1TB -> 1024)
    s = str(x).upper()
    clean = re.sub(r'[^\d]', '', s)
    val = int(clean) if clean else 0
    if 'TB' in s:
        val *= 1024
    return val

def parse_layar(x):
    # Ambil angka desimal untuk layar
    clean = re.sub(r'[^\d\.]', '', str(x).replace(',', '.'))
    return float(clean) if clean else 0.0

def hitung_performa(ram, processor):
    # Performa dihitung berdasarkan kombinasi RAM dan Processor (Skala 0-100)
    proc = str(processor).lower()
    p_score = 50
    if 'i9' in proc or 'ryzen 9' in proc: p_score = 100
    elif 'i7' in proc or 'ryzen 7' in proc: p_score = 80
    elif 'i5' in proc or 'ryzen 5' in proc: p_score = 60
    elif 'i3' in proc or 'ryzen 3' in proc: p_score = 40
    else: p_score = 30
    
    # Skor RAM
    r_score = min(100, ram * 5) # Misal 16GB -> 80, 8GB -> 40
    
    # Bobot: Processor 60%, RAM 40%
    return (p_score * 0.6) + (r_score * 0.4)

df['Harga_Num'] = df['Harga'].apply(parse_harga)
df['RAM_Num'] = df['RAM'].apply(parse_ram)
df['Penyimpanan_Num'] = df['Penyimpanan'].apply(parse_penyimpanan)
df['Layar_Num'] = df['Ukuran Layar'].apply(parse_layar)
df['Performa_Num'] = df.apply(lambda row: hitung_performa(row['RAM_Num'], row['Processor']), axis=1)


# =====================================================================
# 2. DEFINISI VARIABEL FUZZY (FUZZIFIKASI)
# =====================================================================
def trapz(x, a, b, c, d):
    if x <= a or x >= d: return 0.0
    if b <= x <= c: return 1.0
    if a < x < b: return (x - a) / (b - a)
    if c < x < d: return (d - x) / (d - c)
    return 0.0

def trimf(x, a, b, c):
    return trapz(x, a, b, b, c)

def fuzzy_harga(x):
    murah = trapz(x, 0, 0, 6000000, 10000000)
    sedang = trimf(x, 8000000, 13000000, 20000000)
    mahal = trapz(x, 15000000, 25000000, 1e12, 1e12)
    return murah, sedang, mahal

def fuzzy_performa(x):
    rendah = trapz(x, 0, 0, 40, 55)
    menengah = trimf(x, 45, 65, 80)
    tinggi = trapz(x, 70, 85, 100, 100)
    return rendah, menengah, tinggi

def fuzzy_penyimpanan(x):
    kecil = trapz(x, 0, 0, 256, 512)
    cukup = trimf(x, 256, 512, 1024)
    besar = trapz(x, 512, 1024, 10000, 10000)
    return kecil, cukup, besar

# Konstanta Output Skor Kelayakan (Skala 0-100)
SKOR_RENDAH = 30
SKOR_SEDANG = 60
SKOR_TINGGI = 90


# =====================================================================
# 3. BASIS ATURAN FUZZY & 4. IMPLEMENTASI (DEFUZZIFIKASI)
# =====================================================================
def evaluasi_fuzzy(row):
    h_murah, h_sedang, h_mahal = fuzzy_harga(row['Harga_Num'])
    p_rendah, p_menengah, p_tinggi = fuzzy_performa(row['Performa_Num'])
    s_kecil, s_cukup, s_besar = fuzzy_penyimpanan(row['Penyimpanan_Num'])
    
    rules = []
    
    # 1. IF Harga Murah AND Performa Tinggi THEN Skor Tinggi
    rules.append((min(h_murah, p_tinggi), SKOR_TINGGI))
    
    # 2. IF Harga Mahal AND Performa Rendah THEN Skor Rendah
    rules.append((min(h_mahal, p_rendah), SKOR_RENDAH))
    
    # 3. IF Harga Murah AND Performa Menengah AND Penyimpanan Cukup THEN Skor Sedang
    rules.append((min(h_murah, p_menengah, s_cukup), SKOR_SEDANG))
    
    # 4. IF Harga Sedang AND Performa Tinggi THEN Skor Tinggi
    rules.append((min(h_sedang, p_tinggi), SKOR_TINGGI))
    
    # 5. IF Harga Sedang AND Performa Menengah THEN Skor Sedang
    rules.append((min(h_sedang, p_menengah), SKOR_SEDANG))
    
    # 6. IF Harga Mahal AND Performa Tinggi AND Penyimpanan Besar THEN Skor Sedang
    rules.append((min(h_mahal, p_tinggi, s_besar), SKOR_SEDANG))
    
    # 7. IF Harga Murah AND Performa Rendah THEN Skor Rendah
    rules.append((min(h_murah, p_rendah), SKOR_RENDAH))
    
    # 8. IF Performa Tinggi AND Penyimpanan Besar THEN Skor Tinggi
    rules.append((min(p_tinggi, s_besar), SKOR_TINGGI))
    
    # 9. IF Harga Sedang AND Performa Rendah THEN Skor Rendah
    rules.append((min(h_sedang, p_rendah), SKOR_RENDAH))
    
    # 10. IF Penyimpanan Kecil AND Performa Menengah THEN Skor Rendah
    rules.append((min(s_kecil, p_menengah), SKOR_RENDAH))
    
    # Defuzzifikasi (Metode Weighted Average / Rata-rata Terbobot)
    pembilang = sum([r[0] * r[1] for r in rules])
    penyebut = sum([r[0] for r in rules])
    
    if penyebut == 0: 
        return 50.0 # Nilai tengah default jika tidak ada aturan yang aktif
    return pembilang / penyebut

# Terapkan fungsi fuzzy ke setiap baris
df['Skor_Kelayakan'] = df.apply(evaluasi_fuzzy, axis=1)


# =====================================================================
# 5. OUTPUT YANG DIHARAPKAN
# =====================================================================
print("\n" + "="*50)
print(" RINGKASAN STATISTIK DATASET (Data Bersih/Numerik)")
print("="*50)
pd.set_option('display.float_format', lambda x: '%.2f' % x)
stats = df[['Harga_Num', 'RAM_Num', 'Penyimpanan_Num', 'Layar_Num', 'Performa_Num', 'Skor_Kelayakan']].describe()
print(stats)
print("\n")

print("="*60)
print(" TOP 10 LAPTOP DENGAN SKOR KELAYAKAN TERTINGGI")
print("="*60)

df_sorted = df.sort_values(by='Skor_Kelayakan', ascending=False)
for i, row in enumerate(df_sorted.head(10).itertuples(), 1):
    print(f"#{i} - {row.Nama}")
    print(f"     Spesifikasi : {row.Processor} | RAM {row.RAM_Num}GB | SSD {row.Penyimpanan_Num}GB")
    print(f"     Harga       : Rp {row.Harga_Num:,}")
    print(f"     Performa    : {row.Performa_Num:.1f} / 100")
    print(f"     Skor Akhir  : {row.Skor_Kelayakan:.2f} (Kelayakan)")
    print("-" * 60)
