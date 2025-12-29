import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="DompetKu - Pro", page_icon="💸", layout="wide")

# --- KONFIGURASI SALDO & GOOGLE SHEET ---
SALDO_AWAL_FIXED = 4341114  # Ganti sesuai saldo real Anda
NAMA_GOOGLE_SHEET = "Database_Keuangan" 

# --- 2. KONEKSI KE GOOGLE SHEET ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        st.error("Credential Google belum ditemukan di Secrets!")
        st.stop()
        
    client = gspread.authorize(creds)
    return client

def get_data():
    client = init_connection()
    try:
        sheet = client.open(NAMA_GOOGLE_SHEET).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error koneksi Google Sheet: {e}")
        return pd.DataFrame()

def save_data(row_data):
    client = init_connection()
    sheet = client.open(NAMA_GOOGLE_SHEET).sheet1
    sheet.append_row(row_data)

# --- 3. FUNGSI HELPER ---
def format_rupiah(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

def get_month_name(month_int):
    months = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
              "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    return months[month_int]

# --- 4. LOAD DATA & PRE-PROCESSING ---
df = get_data()

if not df.empty:
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Nominal'] = pd.to_numeric(df['Nominal'], errors='coerce')
    # Tambahan kolom bantu untuk Bulan dan Tahun
    df['Bulan'] = df['Tanggal'].dt.month
    df['Tahun'] = df['Tanggal'].dt.year

# --- 5. SIDEBAR (FILTER TAHUN) ---
with st.sidebar:
    st.header("🎛️ Pusat Kontrol")
    
    # Logika Tahun Dinamis (bisa sampai 100 tahun ke depan sesuai data)
    if not df.empty:
        list_tahun = sorted(df['Tahun'].dropna().unique(), reverse=True)
        list_tahun = [int(x) for x in list_tahun]
        current_year = datetime.now().year
        if current_year not in list_tahun:
            list_tahun.insert(0, current_year)
    else:
        list_tahun = [datetime.now().year]

    selected_year = st.selectbox("Pilih Tahun Laporan:", list_tahun)
    st.info("Pilih tahun di atas untuk melihat rekapitulasi spesifik tahun tersebut.")
    st.write("© 2025 DompetKu Pro")

# Filter Data Berdasarkan Tahun Pilihan
if not df.empty:
    df_filtered = df[df['Tahun'] == selected_year]
else:
    df_filtered = df

# --- 6. MAIN DASHBOARD ---
st.title(f"💸 Laporan Keuangan Tahun {selected_year}")

# Tab Menu
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard Utama", "📅 Rekap Bulanan (Detail)", "➕ Input Transaksi", "📝 Raw Data"])

# === TAB 1: DASHBOARD UTAMA ===
with tab1:
    total_pemasukan = 0
    total_pengeluaran_rutin = 0
    total_investasi = 0
    
    if not df_filtered.empty:
        # Hitung Pemasukan
        total_pemasukan = df_filtered[df_filtered['Tipe'] == 'Pemasukan']['Nominal'].sum()
        
        # Hitung Pengeluaran (Non-Investasi)
        # Kita asumsikan Kategori 'Investasi' masuk tipe Pengeluaran tapi kita pisah hitungannya
        mask_pengeluaran = (df_filtered['Tipe'] == 'Pengeluaran') & (df_filtered['Kategori'] != 'Investasi')
        total_pengeluaran_rutin = df_filtered[mask_pengeluaran]['Nominal'].sum()
        
        # Hitung Investasi
        mask_investasi = (df_filtered['Kategori'] == 'Investasi')
        total_investasi = df_filtered[mask_investasi]['Nominal'].sum()
    
    # Saldo Akhir (Akumulasi semua tahun atau tahun ini saja? Biasanya saldo itu akumulasi)
    # Untuk simplifikasi tampilan, kita hitung arus kas tahun ini + Saldo Awal Fixed
    arus_kas_tahun_ini = total_pemasukan - total_pengeluaran_rutin - total_investasi
    saldo_akhir = SALDO_AWAL_FIXED + arus_kas_tahun_ini # Note: Ini simplifikasi, idealnya hitung saldo tahun lalu juga

    # Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Saldo Awal (Fixed)", format_rupiah(SALDO_AWAL_FIXED))
    col2.metric("Total Pemasukan", format_rupiah(total_pemasukan), "➕")
    col3.metric("Pengeluaran Rutin", format_rupiah(total_pengeluaran_rutin), "➖", delta_color="inverse")
    col4.metric("Total Investasi", format_rupiah(total_investasi), "💰", delta_color="off")

    st.markdown("---")
    
    # Big Metric Saldo Akhir
    st.metric(label="💰 Estimasi Saldo Akhir", value=format_rupiah(saldo_akhir), 
              delta=f"Arus Kas Tahun Ini: {format_rupiah(arus_kas_tahun_ini)}")

    # Grafik Tren
    if not df_filtered.empty:
        st.subheader("Tren Arus Kas")
        # Agregasi per bulan
        chart_data = df_filtered.groupby(['Bulan', 'Tipe'])['Nominal'].sum().reset_index()
        # Ganti angka bulan jadi nama bulan agar cantik
        chart_data['Nama Bulan'] = chart_data['Bulan'].apply(get_month_name)
        
        fig_bar = px.bar(chart_data, x='Nama Bulan', y='Nominal', color='Tipe', barmode='group',
                         color_discrete_map={'Pemasukan':'#00CC96', 'Pengeluaran':'#EF553B'},
                         category_orders={"Nama Bulan": [get_month_name(i) for i in range(1,13)]})
        st.plotly_chart(fig_bar, use_container_width=True)

# === TAB 2: REKAP BULANAN (Sesuai Request) ===
with tab2:
    st.subheader(f"🗓️ Rekapitulasi Jan - Des {selected_year}")
    
    if df_filtered.empty:
        st.warning("Belum ada data untuk tahun ini.")
    else:
        # Kita buat struktur data manual agar rapi Jan-Des
        rekap_data = []
        
        for i in range(1, 13): # Bulan 1 sampai 12
            bulan_nama = get_month_name(i)
            
            # Filter data bulan i
            df_bulan = df_filtered[df_filtered['Bulan'] == i]
            
            pemasukan_bln = df_bulan[df_bulan['Tipe'] == 'Pemasukan']['Nominal'].sum()
            
            # Pengeluaran Rutin (Exclude Investasi)
            pengeluaran_bln = df_bulan[
                (df_bulan['Tipe'] == 'Pengeluaran') & 
                (df_bulan['Kategori'] != 'Investasi')
            ]['Nominal'].sum()
            
            # Investasi
            investasi_bln = df_bulan[df_bulan['Kategori'] == 'Investasi']['Nominal'].sum()
            
            # Sisa (Net Flow Bulan itu)
            sisa_bln = pemasukan_bln - pengeluaran_bln - investasi_bln
            
            if pemasukan_bln > 0 or pengeluaran_bln > 0 or investasi_bln > 0:
                rekap_data.append({
                    "Bulan": bulan_nama,
                    "Pemasukan": pemasukan_bln,
                    "Pengeluaran": pengeluaran_bln,
                    "Investasi": investasi_bln,
                    "Arus Kas (Sisa)": sisa_bln
                })
        
        if rekap_data:
            df_rekap = pd.DataFrame(rekap_data)
            
            # Format tampilan angka untuk tabel
            df_tampil = df_rekap.copy()
            cols_num = ["Pemasukan", "Pengeluaran", "Investasi", "Arus Kas (Sisa)"]
            for c in cols_num:
                df_tampil[c] = df_tampil[c].apply(format_rupiah)
                
            st.dataframe(df_tampil, use_container_width=True, hide_index=True)
            
            # Visualisasi Breakdown
            st.caption("Grafik Perbandingan Komponen Keuangan Per Bulan")
            fig_line = px.line(df_rekap, x='Bulan', y=['Pemasukan', 'Pengeluaran', 'Investasi'], 
                               markers=True, title="Dinamika Keuangan Bulanan")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Belum ada transaksi tercatat di bulan-bulan tahun ini.")

# === TAB 3: INPUT TRANSAKSI ===
with tab3:
    st.subheader("Input Transaksi Baru")
    
    with st.container(border=True):
        with st.form("form_transaksi", clear_on_submit=True):
            col_in1, col_in2 = st.columns(2)
            
            with col_in1:
                tanggal_input = st.date_input("Tanggal Transaksi", datetime.now())
                tipe_input = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
                nominal_input = st.number_input("Nominal (Rp)", min_value=0, step=10000)

            with col_in2:
                # Logika Pilihan Kategori sesuai Request
                if tipe_input == "Pemasukan":
                    opsi_kategori = ["Gaji", "Tunjangan Pemkot", "Bonus", "Lainnya"]
                else:
                    opsi_kategori = ["Operasional", "Ojek Sekolah", "Investasi", "Makan & Minum", "Belanja", "Lainnya"]
                
                kategori_select = st.selectbox("Kategori", opsi_kategori)
                
                # Jika pilih 'Lainnya', muncul text input manual
                kategori_manual = ""
                if kategori_select == "Lainnya":
                    kategori_manual = st.text_input("Tulis Nama Kategori Lainnya")
                
                catatan_input = st.text_input("Catatan Tambahan (Opsional)")
            
            st.markdown("---")
            submitted = st.form_submit_button("💾 Simpan ke Database", use_container_width=True)

            if submitted:
                # Tentukan kategori final
                kategori_final = kategori_manual if kategori_select == "Lainnya" else kategori_select
                
                if nominal_input > 0 and kategori_final:
                    with st.spinner("Mengirim data ke Google Sheet..."):
                        tgl_str = tanggal_input.strftime("%Y-%m-%d")
                        # Urutan kolom di GSheet harus: Tanggal, Tipe, Kategori, Nominal, Catatan
                        data_baru = [tgl_str, tipe_input, kategori_final, nominal_input, catatan_input]
                        save_data(data_baru)
                        st.success("Data berhasil disimpan!")
                        st.rerun()
                else:
                    st.error("Mohon isi Nominal dan Kategori dengan benar.")

# === TAB 4: RAW DATA ===
with tab4:
    st.subheader("Database Keseluruhan")
    if not df_filtered.empty:
        # Download Button
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name=f"keuangan_{selected_year}.csv", mime='text/csv')
        
        tabel_raw = df_filtered[['Tanggal', 'Tipe', 'Kategori', 'Nominal', 'Catatan']].copy()
        tabel_raw['Nominal'] = tabel_raw['Nominal'].apply(format_rupiah)
        tabel_raw['Tanggal'] = tabel_raw['Tanggal'].dt.strftime('%d-%m-%Y')
        st.dataframe(tabel_raw, use_container_width=True, hide_index=True)
    else:
        st.write("Data kosong.")
