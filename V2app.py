import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="DompetKu - Cloud", page_icon="💸", layout="wide")

# --- KONFIGURASI SALDO & GOOGLE SHEET ---
SALDO_AWAL_FIXED = 4341114  # Ganti sesuai saldo real Anda
NAMA_GOOGLE_SHEET = "Database_Keuangan" # Pastikan nama file di GSheet SAMA PERSIS

# --- 2. KONEKSI KE GOOGLE SHEET ---
# Fungsi ini menggunakan cache agar tidak loading ulang terus menerus
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Mendeteksi Secrets dari Streamlit Cloud atau Local
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Fallback jika dijalankan manual tanpa secrets (Opsional, tapi lebih baik pakai Secrets)
        st.error("Credential Google belum ditemukan di Secrets!")
        st.stop()
        
    client = gspread.authorize(creds)
    return client

# Fungsi ambil data
def get_data():
    client = init_connection()
    try:
        sheet = client.open(NAMA_GOOGLE_SHEET).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error koneksi Google Sheet: {e}")
        return pd.DataFrame()

# Fungsi simpan data
def save_data(row_data):
    client = init_connection()
    sheet = client.open(NAMA_GOOGLE_SHEET).sheet1
    sheet.append_row(row_data)

# --- 3. FUNGSI HELPER ---
def format_rupiah(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- 4. LOAD DATA DARI INTERNET ---
df = get_data()

# Pre-processing Tanggal
if not df.empty:
    # Mengatasi format tanggal yang mungkin tercampur di GSheet
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Nominal'] = pd.to_numeric(df['Nominal'], errors='coerce')

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Pusat Kontrol")
    if not df.empty:
        list_tahun = sorted(df['Tanggal'].dt.year.dropna().unique(), reverse=True)
        list_tahun = [int(x) for x in list_tahun]
        current_year = datetime.now().year
        if current_year not in list_tahun:
            list_tahun.insert(0, current_year)
    else:
        list_tahun = [datetime.now().year]

    selected_year = st.selectbox("Pilih Tahun:", list_tahun)
    st.write("© 2025 DompetKu Cloud")

# Filter Data
if not df.empty:
    df_filtered = df[df['Tanggal'].dt.year == selected_year]
else:
    df_filtered = df

# --- 6. MAIN DASHBOARD ---
st.title(f"💸 Keuangan Online {selected_year}")
st.caption(f"Terhubung ke Google Sheet: {NAMA_GOOGLE_SHEET}")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Input Cloud", "📝 Tabel Data"])

# === TAB 1: DASHBOARD ===
with tab1:
    total_pemasukan = 0
    total_pengeluaran = 0
    
    if not df_filtered.empty:
        total_pemasukan = df_filtered[df_filtered['Tipe'] == 'Pemasukan']['Nominal'].sum()
        total_pengeluaran = df_filtered[df_filtered['Tipe'] == 'Pengeluaran']['Nominal'].sum()
    
    saldo_akhir = SALDO_AWAL_FIXED + total_pemasukan - total_pengeluaran

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Saldo Awal", format_rupiah(SALDO_AWAL_FIXED))
    col2.metric("Masuk", format_rupiah(total_pemasukan), "➕")
    col3.metric("Keluar", format_rupiah(total_pengeluaran), "➖", delta_color="inverse")
    
    kenaikan = saldo_akhir - SALDO_AWAL_FIXED
    col4.metric("Saldo Akhir", format_rupiah(saldo_akhir), 
                delta=f"{format_rupiah(kenaikan)}",
                delta_color="normal" if kenaikan >= 0 else "inverse")

    st.markdown("---")
    
    if not df_filtered.empty:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            fig_pie = px.pie(df_filtered, values='Nominal', names='Tipe', title="Komposisi", 
                             color='Tipe', color_discrete_map={'Pemasukan':'#00CC96', 'Pengeluaran':'#EF553B'})
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_c2:
            daily = df_filtered.groupby(['Tanggal', 'Tipe'])['Nominal'].sum().reset_index()
            fig_bar = px.bar(daily, x='Tanggal', y='Nominal', color='Tipe', title="Tren Harian",
                             color_discrete_map={'Pemasukan':'#00CC96', 'Pengeluaran':'#EF553B'})
            st.plotly_chart(fig_bar, use_container_width=True)

# === TAB 2: INPUT ===
with tab2:
    st.subheader("Input ke Google Sheet")
    with st.form("form_transaksi", clear_on_submit=True):
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            tanggal_input = st.date_input("Tanggal", datetime.now())
            tipe_input = st.selectbox("Tipe", ["Pemasukan", "Pengeluaran"])
            nominal_input = st.number_input("Nominal (Rp)", min_value=0, step=10000)
        with col_in2:
            kategori_input = st.text_input("Kategori")
            catatan_input = st.text_input("Catatan")
        
        submitted = st.form_submit_button("Kirim ke Database 🚀", use_container_width=True)

        if submitted:
            if nominal_input > 0 and kategori_input:
                with st.spinner("Menyimpan ke Google Sheet..."):
                    # Format data list untuk dikirim ke GSheet
                    # Tanggal diubah jadi string biar GSheet tidak bingung
                    tgl_str = tanggal_input.strftime("%Y-%m-%d")
                    
                    data_baru = [tgl_str, tipe_input, kategori_input, nominal_input, catatan_input]
                    save_data(data_baru)
                    
                    st.success("Data berhasil masuk Cloud! Refreshing...")
                    st.rerun()
            else:
                st.error("Nominal & Kategori wajib diisi.")

# === TAB 3: TABEL ===
with tab3:
    if not df_filtered.empty:
        tabel_show = df_filtered.copy()
        tabel_show['Nominal'] = tabel_show['Nominal'].apply(format_rupiah)
        tabel_show['Tanggal'] = tabel_show['Tanggal'].dt.strftime('%d-%m-%Y')
        st.dataframe(tabel_show, use_container_width=True, hide_index=True)
