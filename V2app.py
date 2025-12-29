import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="DompetKu - Aplikasi Keuangan",
    page_icon="💸",
    layout="wide"
)

# --- KONFIGURASI SALDO AWAL ---
SALDO_AWAL_FIXED = 4341114 

# --- 2. INISIALISASI DATABASE ---
if 'data_transaksi' not in st.session_state:
    st.session_state['data_transaksi'] = []

# --- 3. FUNGSI HELPER ---
def format_rupiah(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- 4. DATA PRE-PROCESSING ---
df = pd.DataFrame(st.session_state['data_transaksi'])
if not df.empty:
    # Konversi ke datetime, handle error jika format salah
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')

# --- 5. SIDEBAR (MENU KIRI) ---
with st.sidebar:
    st.header("🎛️ Pusat Kontrol")
    
    # Logic Tahun agar tidak error jika data kosong
    if not df.empty and df['Tanggal'].notna().any():
        list_tahun = sorted(df['Tanggal'].dt.year.dropna().unique(), reverse=True)
        current_year = datetime.now().year
        if current_year not in list_tahun:
            list_tahun.insert(0, current_year)
    else:
        list_tahun = [datetime.now().year]

    # Pastikan list_tahun bersih dari nilai float/NaN
    list_tahun = [int(x) for x in list_tahun]
    
    selected_year = st.selectbox("Pilih Tahun Rekap:", list_tahun)
    
    st.info(f"Tahun: **{selected_year}**")
    st.write("© 2025 DompetKu App")

# Filter Data
if not df.empty:
    df_filtered = df[df['Tanggal'].dt.year == selected_year]
else:
    df_filtered = df

# --- 6. HEADER ---
st.title(f"💸 Laporan Keuangan {selected_year}")
st.markdown("Aplikasi Pencatat Keuangan Pribadi (Web Version)")

# --- 7. TABS MENU ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Input", "📝 Tabel"])

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
        # Chart 1: Pie
        pie_data = pd.DataFrame({
            "Tipe": ["Pemasukan", "Pengeluaran"],
            "Total": [total_pemasukan, total_pengeluaran]
        })
        fig_pie = px.pie(pie_data, values='Total', names='Tipe', 
                            color='Tipe', color_discrete_map={'Pemasukan':'#00CC96', 'Pengeluaran':'#EF553B'},
                            hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Belum ada transaksi tambahan.")

# === TAB 2: INPUT TRANSAKSI ===
with tab2:
    st.subheader("Tambah Transaksi")
    with st.form("form_transaksi", clear_on_submit=True):
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            tanggal_input = st.date_input("Tanggal", datetime.now())
            tipe_input = st.selectbox("Jenis", ["Pemasukan", "Pengeluaran"])
            nominal_input = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        with col_in2:
            kategori_input = st.text_input("Kategori", placeholder="Misal: Makan")
            catatan_input = st.text_input("Catatan")
        
        simpan = st.form_submit_button("Simpan", use_container_width=True)

        if simpan:
            if nominal_input > 0 and kategori_input:
                new_data = {
                    "Tanggal": pd.Timestamp(tanggal_input),
                    "Tipe": tipe_input,
                    "Kategori": kategori_input,
                    "Nominal": nominal_input,
                    "Catatan": catatan_input
                }
                st.session_state['data_transaksi'].append(new_data)
                st.success("Tersimpan!")
                st.rerun()
            else:
                st.error("Nominal & Kategori wajib diisi.")

# === TAB 3: TABEL DATA ===
with tab3:
    if not df_filtered.empty:
        tabel_show = df_filtered.copy()
        tabel_show['Nominal'] = tabel_show['Nominal'].apply(format_rupiah)
        tabel_show['Tanggal'] = tabel_show['Tanggal'].dt.strftime('%d-%m-%Y')
        st.dataframe(tabel_show, use_container_width=True, hide_index=True)