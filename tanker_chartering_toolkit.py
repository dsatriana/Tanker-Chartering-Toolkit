"""
Tanker Chartering Toolkit (Merged, disesuaikan pasar Indonesia)
================================================================
Gabungan dua kalkulator chartering tanker menjadi satu toolkit, tanpa modul
yang tumpang tindih, dan disesuaikan untuk konteks pasar Indonesia (khususnya
voyage domestik/cabotase) sambil tetap mempertahankan standar global
(Worldscale, USD) untuk voyage internasional.

  1. Worldscale Freight Calculator      — standar GLOBAL, tetap dipertahankan
                                           utuh untuk voyage internasional.
  2. Voyage Estimate & TCE Calculator   — gabungan terlengkap dari kedua
                                           project sumber, kini dengan:
                                             - toggle Domestik (cabotase) /
                                               Internasional
                                             - toggle mata uang USD / IDR
                                             - preset ukuran kapal (kapal
                                               kecil/menengah domestik vs
                                               kapal besar internasional)
                                             - opsi rincian biaya pelabuhan
                                               gaya Indonesia (Pelindo/PNBP:
                                               labuh, tambat, pandu, tunda,
                                               dermaga/PBM)
  3. Laytime & Demurrage/Despatch       — universal, dengan toggle mata uang
                                           USD/IDR untuk fixture domestik.

Modul "Charter Party Reference" dari salah satu project sumber SENGAJA
dihapus atas permintaan pengguna (referensi statis, bentuk kontrak oil-major
yang jarang dipakai pada fixture domestik Indonesia).

Alat bantu edukasi/estimasi. Bukan pengganti wording charter party yang
sebenarnya, tabel Worldscale berlisensi resmi, tarif PNBP/Pelindo resmi, kurs
live, atau nasihat komersial/hukum profesional. Lihat catatan konteks pasar
Indonesia di tab Ringkasan.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import datetime as dt

APP_DIR = Path(__file__).parent

# ----------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Tanker Chartering Toolkit",
    page_icon="🛢️",
    layout="wide",
)


@st.cache_data
def load_ports():
    path = APP_DIR / "indonesia_ports.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame({"portname": [], "region": []})


ports_df = load_ports()
port_options = ["(Pelabuhan lain / manual)"] + sorted(ports_df["portname"].tolist())

# Preset ukuran kapal — angka ilustratif/ballpark, BUKAN data manufaktur resmi.
# Kapal kecil/menengah mencerminkan armada domestik Indonesia yang umumnya
# jauh lebih kecil dari kapal parcel/crude internasional (Aframax/VLCC dst.).
VESSEL_PRESETS = {
    "Kapal kecil domestik (± 3.000–5.000 DWT, coaster)": dict(
        voy_qty=3_000.0, voy_speed_laden=9.5, voy_speed_ballast=10.0,
        voy_ifo_laden=0.0, voy_ifo_ballast=0.0, voy_ifo_port=0.0,
        voy_mdo_sea=3.5, voy_mdo_port=1.0,
    ),
    "Kapal menengah domestik (± 6.500–17.500 DWT)": dict(
        voy_qty=12_000.0, voy_speed_laden=11.0, voy_speed_ballast=11.5,
        voy_ifo_laden=6.0, voy_ifo_ballast=5.0, voy_ifo_port=0.5,
        voy_mdo_sea=1.0, voy_mdo_port=1.0,
    ),
    "Kapal besar / rute internasional (mis. Aframax 80.000+ DWT)": dict(
        voy_qty=80_000.0, voy_speed_laden=12.5, voy_speed_ballast=13.0,
        voy_ifo_laden=28.0, voy_ifo_ballast=26.0, voy_ifo_port=3.0,
        voy_mdo_sea=1.0, voy_mdo_port=2.0,
    ),
}

st.title("🛢️ Tanker Chartering Toolkit")
st.caption("Worldscale freight · Voyage estimate (TCE) · Laytime & demurrage/despatch")

tab_home, tab_ws, tab_voy, tab_lay = st.tabs(
    [
        "🏠 Ringkasan",
        "⚓ Worldscale Freight",
        "🧮 Voyage Estimate (TCE)",
        "⏱️ Laytime & Demurrage",
    ]
)

# ==============================================================================
# TAB 0 — HOME
# ==============================================================================
with tab_home:
    st.subheader("Tentang toolkit ini")
    st.markdown(
        """
Tiga modul yang saling terkait, disusun mengikuti alur kerja chartering desk /
voyage estimator untuk tanker:

| Modul | Fungsi |
|---|---|
| **⚓ Worldscale Freight** | Konversi flat rate (WS100) + WS% menjadi freight USD. Standar **global**, dipakai terutama untuk voyage internasional. Hasilnya bisa ditarik langsung ke tab Voyage Estimate. |
| **🧮 Voyage Estimate (TCE)** | Gabungkan freight, bunker (2 grade), biaya pelabuhan/kanal, dan waktu voyage (laden/ballast terpisah) menjadi TCE — dengan toggle **Domestik/Internasional**, **USD/IDR**, preset ukuran kapal, dan pilihan rincian biaya pelabuhan gaya Indonesia (Pelindo). |
| **⏱️ Laytime & Demurrage** | Hitung allowed laytime, waktu terpakai, dan demurrage/despatch payable — berlaku universal, dengan pilihan mata uang USD/IDR. |

Freight rate dari tab Worldscale bisa ditarik langsung ke tab Voyage Estimate
(pilih basis freight "Dari Worldscale") — tanpa perlu memasukkan flat rate &
WS% dua kali.
        """
    )

    st.warning(
        "⚠️ **Disclaimer:** Ini alat bantu edukasi/estimasi. Flat rate Worldscale "
        "aktual bersifat proprietary (berlangganan). Tarif pelabuhan gaya Pelindo/PNBP "
        "pada tab Voyage Estimate adalah **struktur ilustratif** (bukan tabel tarif resmi "
        "terbaru) — isi dengan tarif aktual dari agen/Pelindo setempat. Kurs USD/IDR yang "
        "ditampilkan adalah **referensi ilustratif saja, bukan kurs live** — selalu cek "
        "kurs terkini sebelum dipakai untuk keputusan komersial. Daftar pelabuhan Indonesia "
        "pada tab Voyage Estimate adalah contoh awal (starter list), bukan basis data resmi."
    )

    with st.expander("🇮🇩 Catatan konteks pasar Indonesia", expanded=True):
        st.markdown(
            """
- **Worldscale** dirancang untuk fixture tanker **internasional** pada rute-rute
  yang sudah punya flat rate resmi. Ini relevan untuk voyage lintas negara yang
  melibatkan pelabuhan Indonesia (ekspor/impor crude & products), tapi **tidak
  dipakai** untuk pelayaran domestik antar-pulau — karena itu, opsi "Dari
  Worldscale" otomatis disembunyikan saat Anda memilih mode **Domestik** di
  tab Voyage Estimate, dan hanya muncul lagi pada mode **Internasional**.
- Pelayaran domestik Indonesia tunduk pada **asas cabotage** (Inpres No.
  5/2005 dan aturan turunannya): kapal harus berbendera Indonesia & dioperasikan
  perusahaan pelayaran nasional. Ini faktor **kelayakan/kepatuhan**, bukan
  sesuatu yang otomatis dicek kalkulator — muncul sebagai pengingat saat mode
  Domestik dipilih.
- Armada domestik Indonesia (products/CPO/BBM/aspal, dsb.) umumnya jauh **lebih
  kecil** dari kapal parcel/crude internasional — karena itu tab Voyage Estimate
  kini punya **preset ukuran kapal** (kecil/menengah domestik vs besar
  internasional) agar default kecepatan & konsumsi bahan bakar tidak bias ke
  ukuran kapal internasional.
- Biaya pelabuhan domestik umumnya mengikuti struktur **Pelindo/PNBP** (labuh,
  tambat, pandu, tunda, dermaga/PBM) — bukan satu angka lumpsum "port
  disbursement" seperti kebiasaan agensi internasional. Tab Voyage Estimate
  punya opsi untuk merinci biaya dengan struktur ini.
- Fixture domestik lazim dinegosiasikan dalam **Rupiah**, sedangkan fixture
  internasional & Worldscale selalu dalam **USD** — tab Voyage Estimate & tab
  Laytime kini punya toggle mata uang untuk ini.
- Istilah bahan bakar "IFO" dan "MDO" dipertahankan sesuai kebiasaan lama;
  sejak IMO 2020 sebagian besar kapal tanpa scrubber memakai **VLSFO** &
  **LSMGO**, dan banyak kapal kecil domestik hanya memakai satu jenis bahan
  bakar (MDO/MGO/Solar) sama sekali tanpa HFO — preset kapal kecil domestik
  sudah mencerminkan ini (konsumsi grade pertama = 0).
            """
        )

    with st.expander("📚 Sumber & referensi", expanded=False):
        st.markdown(
            """
**Worldscale**
- Worldscale Association (London) Ltd. / Worldscale Association (NYC) Inc. — penerbit resmi
  *New Worldwide Tanker Nominal Freight Scale* tahunan — [worldscale.co.uk](https://www.worldscale.co.uk)
- Baltic Exchange — [Guide to Modern Shipping: Tanker Chartering](https://www.balticexchange.com/en/who-we-are/guide-to-modern-shipping/tanker-chartering.html)
- INTERTANKO — [Topics & Issues: Worldscale](https://www.intertanko.com/topics-issues/issue/worldscale)
- Wikipedia — [Worldscale](https://en.wikipedia.org/wiki/Worldscale)
- gCaptain — contoh flat rate 2026 Houston–New York, [Waiving the Jones Act Won't Lower Gas Prices](https://gcaptain.com/opinion-waiving-the-jones-act-wont-lower-gas-prices-tanker-markets-prove-it/)

**Laytime & demurrage**
- Handybulk — seri artikel [Laytime](https://www.handybulk.com/laytime/),
  [Calculation of Demurrage](https://www.handybulk.com/calculation-of-demurrage),
  [Laytime, Demurrage & Despatch Explained](https://www.handybulk.com/laytime-demurrage-and-despatch-in-ship-chartering-explained/)
- Heisenberg Shipping — [Online Laytime Calculator](https://heisenbergshipping.com/online-laytime-calculator-tool/) (konvensi despatch = 50% demurrage)

**Voyage estimate & TCE**
- Handybulk — [Voyage Estimation: Time at Sea](https://www.handybulk.com/voyage-estimation-time-at-sea-distance-speed-bunker-consumption-weather-allowance-and-tce/),
  [Voyage Estimation: Port Days & TCE](https://www.handybulk.com/?p=1813),
  [TCE — Time Charter Equivalent](https://www.handybulk.com/tce-time-charter-equivalent/)
- The Signal Group — [TCE Benchmarking: A Tanker Operator's Guide](https://www.thesignalgroup.com/newsroom/tce-benchmarking-tanker-operators-guide)
- Heisenberg Shipping — [Time Charter Equivalent (TCE)](https://heisenbergshipping.com/time-charter-equivalent-tce/)

**Konteks pasar Indonesia**
- Asas cabotage: Instruksi Presiden No. 5 Tahun 2005 tentang Pemberdayaan Industri
  Pelayaran Nasional, dan Undang-Undang No. 17 Tahun 2008 tentang Pelayaran.
- Struktur tarif pelabuhan (labuh, tambat, pandu, tunda, dermaga) mengikuti
  praktik umum PNBP kepelabuhanan Indonesia (PT Pelindo) — cek tarif resmi
  terbaru pada agen/Pelindo setempat, karena berubah dari waktu ke waktu.

Semua angka default (harga bunker, biaya pelabuhan, freight rate, kurs, dsb.)
adalah **placeholder** untuk demonstrasi — ganti dengan data pasar terkini
Anda sebelum dipakai untuk keputusan komersial.
            """
        )

# ==============================================================================
# TAB 1 — WORLDSCALE FREIGHT CALCULATOR (standar global — tidak diubah)
# ==============================================================================
with tab_ws:
    st.subheader("⚓ Worldscale Freight Calculator")
    st.caption("Standar global — dipertahankan penuh untuk voyage internasional.")
    st.markdown(
        """
**Worldscale (WS)** adalah sistem referensi standar untuk menegosiasikan freight
tanker. Setiap tahun, *Worldscale Association (London) Ltd* dan
*Worldscale Association (NYC) Inc* menerbitkan **flat rate (WS100)** — dalam
USD per metric ton — untuk ratusan ribu kombinasi rute pelabuhan muat/bongkar,
dihitung berdasarkan kapal notional **75.000 DWT**, kecepatan dinas **14,5 knot**,
konsumsi bunker transit **55 MT/hari**, dan waktu pelabuhan tetap **4 hari**, agar
setiap voyage secara teoritis menghasilkan *daily return* yang setara bagi owner.
Freight aktual dinegosiasikan sebagai **persentase dari flat rate** — 1 WS point = 1%.
        """
    )
    st.latex(r"\text{Freight (USD)} = \text{Cargo Qty (MT)} \times \text{Flat Rate WS100 (USD/MT)} \times \frac{\text{WS\%}}{100}")

    col1, col2 = st.columns(2)
    with col1:
        ws_qty = st.number_input(
            "Cargo Quantity (MT)", min_value=1.0, value=80_000.0, step=1_000.0, key="ws_qty"
        )
        ws_flat = st.number_input(
            "Flat Rate — WS100 (USD/MT)",
            min_value=0.0,
            value=10.88,
            step=0.01,
            key="ws_flat",
            help="Contoh ilustratif: flat rate Houston–New York 2026 = USD 10.88/mt (gCaptain, 2026). "
            "Masukkan flat rate dari tabel Worldscale berlisensi Anda untuk rute yang sesungguhnya.",
        )
    with col2:
        ws_pct = st.number_input(
            "WS Level pasar (%)", min_value=0.0, value=100.0, step=1.0, key="ws_pct",
            help="WS100 = 100% dari flat rate, WS75 = diskon 25%, WS410 = premium 310% dst.",
        )
        ws_comm = st.number_input(
            "Address Commission (%)", min_value=0.0, value=1.25, step=0.05, key="ws_comm"
        )

    ws_gross = ws_qty * ws_flat * (ws_pct / 100.0)
    ws_comm_amt = ws_gross * (ws_comm / 100.0)
    ws_net = ws_gross - ws_comm_amt
    ws_rate_per_mt = ws_flat * (ws_pct / 100.0)

    # Simpan hasil supaya bisa ditarik langsung oleh tab Voyage Estimate & TCE
    st.session_state["ws_rate_per_mt"] = ws_rate_per_mt
    st.session_state["ws_qty_last"] = ws_qty

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rate efektif (USD/MT)", f"${ws_rate_per_mt:,.3f}")
    m2.metric("Gross Freight", f"${ws_gross:,.0f}")
    m3.metric(f"Komisi ({ws_comm:.2f}%)", f"${ws_comm_amt:,.0f}")
    m4.metric("Net Freight", f"${ws_net:,.0f}")

    st.info(
        "➡️ Rate efektif di atas otomatis tersedia di tab **🧮 Voyage Estimate (TCE)** "
        "saat mode **Internasional** dipilih — opsi \"Dari Worldscale\" akan terisi "
        "otomatis dengan nilai ini (tetap bisa diedit manual)."
    )

    st.markdown("###### Contoh ilustratif flat rate (bukan tabel resmi — hanya untuk orientasi)")
    example_df = pd.DataFrame(
        [
            {"Rute": "Yokohama → Adelaide", "Flat Rate (USD/MT)": 10.60, "Jarak (nm)": 10_574, "Sumber": "Wikipedia — Worldscale"},
            {"Rute": "Houston → New York (2026)", "Flat Rate (USD/MT)": 10.88, "Jarak (nm)": "-", "Sumber": "gCaptain, 2026"},
        ]
    )
    st.dataframe(example_df, hide_index=True, use_container_width=True)
    st.caption(
        "Tabel flat rate resmi & lengkap bersifat berlangganan — akses melalui Worldscale Association "
        "(worldscale.co.uk) atau penyedia harga seperti Platts/S&P Global Commodity Insights, Argus, atau Baltic Exchange. "
        "Worldscale umumnya dipakai untuk fixture *internasional*, bukan pelayaran domestik dalam negeri Indonesia."
    )

# ==============================================================================
# TAB 2 — VOYAGE ESTIMATE / TCE CALCULATOR (gabungan + disesuaikan Indonesia)
# ==============================================================================
with tab_voy:
    st.subheader("🧮 Voyage Estimate & TCE Calculator")
    st.markdown(
        """
**Time Charter Equivalent (TCE)** menormalkan hasil sebuah voyage charter ke
basis harian, sehingga bisa dibandingkan langsung dengan tawaran time charter
hire — untuk voyage domestik maupun internasional.
        """
    )
    st.latex(
        r"\text{TCE (per hari)} = \frac{\text{Net Freight} - \text{Voyage Costs}}{\text{Voyage Days}} \;(+\, \text{OPEX/hari, opsional})"
    )

    # ---- 0) Tipe voyage & mata uang ----
    st.markdown("##### 0) Tipe voyage & mata uang")
    c1, c2 = st.columns(2)
    with c1:
        voyage_type = st.radio(
            "Tipe voyage",
            ["🇮🇩 Domestik (cabotase)", "🌍 Internasional"],
            horizontal=True,
            key="voy_type",
        )
        is_domestic = voyage_type.startswith("🇮🇩")
        if is_domestic:
            st.info(
                "Voyage domestik tunduk pada **asas cabotage** (Inpres No. 5/2005 & "
                "UU No. 17/2008 tentang Pelayaran): kapal harus berbendera Indonesia "
                "dan dioperasikan perusahaan pelayaran nasional. Kalkulator ini tidak "
                "mengecek kepatuhan tersebut secara otomatis — pastikan kelayakan ini "
                "terpenuhi sebelum fixture."
            )
    with c2:
        default_currency_index = 1 if is_domestic else 0
        currency = st.radio(
            "Mata uang tampilan",
            ["USD ($)", "IDR (Rp)"],
            horizontal=True,
            index=default_currency_index,
            key="voy_currency",
        )
        symbol = "$" if currency.startswith("USD") else "Rp"
        fx_rate = st.number_input(
            "Kurs referensi (Rp per USD) — info silang saja, tidak memengaruhi kalkulasi",
            min_value=0.0,
            value=17_700.0,
            step=50.0,
            key="voy_fx_rate",
            help="Ilustrasi saja (kurs pertengahan September 2026 berkisar ~Rp17.700/USD) — "
            "BUKAN kurs live. Cek kurs aktual sebelum dipakai untuk keputusan komersial.",
        )

    def d(usd_value: float) -> float:
        """Skala nilai default USD ke IDR (ilustrasi) bila mata uang = IDR."""
        return usd_value if symbol == "$" else round(usd_value * fx_rate, -3)

    # ---- Preset ukuran kapal ----
    st.markdown("##### Preset ukuran kapal (opsional)")
    preset_choice = st.selectbox(
        "Pilih preset untuk mengisi otomatis kecepatan & konsumsi di bawah (bisa diedit manual setelahnya)",
        ["(Manual / custom — tidak mengubah apa pun)"] + list(VESSEL_PRESETS.keys()),
        key="voy_preset",
    )
    if preset_choice in VESSEL_PRESETS:
        if st.button("Terapkan preset ke input di bawah", key="voy_apply_preset"):
            for k, v in VESSEL_PRESETS[preset_choice].items():
                st.session_state[k] = v
            st.rerun()
    st.caption(
        "Preset bersifat ilustratif (bukan data manufaktur kapal spesifik) — dibuat karena "
        "armada domestik Indonesia umumnya jauh lebih kecil dari kapal parcel/crude "
        "internasional. Preset kapal kecil domestik sengaja tidak memakai bahan bakar grade "
        "pertama (mis. IFO/HFO) karena kapal sekecil itu umumnya hanya berbahan bakar "
        "MDO/MGO/Solar."
    )

    sub_cargo, sub_speed, sub_days, sub_bunker = st.tabs(
        ["🗺️ Voyage & Freight", "🚢 Kecepatan & Konsumsi", "⚓ Hari & Biaya Pelabuhan", "⛽ Harga Bunker"]
    )

    # ---- Sub-tab: Voyage & Freight ----
    with sub_cargo:
        c1, c2 = st.columns(2)
        with c1:
            load_port = st.selectbox("Pelabuhan muat (load port)", port_options, index=0, key="voy_load_port")
            laden_distance = st.number_input(
                "Jarak laden (load → discharge), NM", min_value=0.0, value=800.0, step=10.0, key="voy_laden_nm"
            )
            cargo_qty = st.number_input(
                "Jumlah cargo (MT)", min_value=1.0, value=50_000.0, step=100.0, key="voy_qty"
            )
            has_ballast = st.checkbox("Sertakan voyage ballast (posisi awal → load port)", value=True, key="voy_has_ballast")
            ballast_distance = st.number_input(
                "Jarak ballast (posisi awal → load port), NM",
                min_value=0.0,
                value=300.0,
                step=10.0,
                disabled=not has_ballast,
                key="voy_ballast_nm",
            )
        with c2:
            discharge_port = st.selectbox(
                "Pelabuhan bongkar (discharge port)", port_options, index=0, key="voy_disch_port"
            )

            # Worldscale hanya relevan untuk voyage internasional
            if is_domestic:
                freight_options = ["Rate langsung (per MT)", "Lumpsum"]
            else:
                freight_options = ["Rate langsung (per MT)", "Lumpsum", "Dari Worldscale (tab sebelumnya)"]
            if st.session_state.get("voy_freight_mode") not in freight_options:
                st.session_state["voy_freight_mode"] = freight_options[0]
            freight_mode = st.radio("Basis freight", freight_options, key="voy_freight_mode")

            if freight_mode == "Rate langsung (per MT)":
                freight_rate = st.number_input(
                    f"Freight rate ({symbol}/MT)", min_value=0.0, value=d(12.0), step=0.5, key="voy_rate"
                )
                gross_freight = freight_rate * cargo_qty
            elif freight_mode == "Lumpsum":
                gross_freight = st.number_input(
                    f"Freight lumpsum ({symbol})", min_value=0.0, value=d(600_000.0), step=1_000.0, key="voy_lumpsum"
                )
                freight_rate = gross_freight / cargo_qty if cargo_qty else 0
            else:
                ws_rate_default = st.session_state.get("ws_rate_per_mt", 0.0)
                if ws_rate_default == 0.0:
                    st.warning(
                        "Belum ada hasil dari tab ⚓ Worldscale Freight. Buka tab itu dulu, "
                        "atau isi rate secara manual di bawah."
                    )
                freight_rate = st.number_input(
                    "Freight rate dari Worldscale (USD/MT)",
                    min_value=0.0,
                    value=float(ws_rate_default),
                    step=0.01,
                    key="voy_ws_rate",
                    help="Terisi otomatis dari perhitungan tab Worldscale Freight (bisa diedit manual). "
                    "Selalu dalam USD karena Worldscale tidak diterbitkan dalam mata uang lain.",
                )
                gross_freight = freight_rate * cargo_qty
                if symbol == "Rp":
                    st.caption(
                        "⚠️ Freight di atas tetap dalam **USD** (bawaan Worldscale). Bila tampilan "
                        "Anda diset ke IDR, konversikan manual memakai kurs referensi di atas."
                    )
            addr_comm = st.number_input("Address commission (%)", min_value=0.0, value=1.25, step=0.25, key="voy_addr_comm")
            broker_comm = st.number_input("Brokerage commission (%)", min_value=0.0, value=1.25, step=0.25, key="voy_broker_comm")

    # ---- Sub-tab: Speed & Consumption ----
    with sub_speed:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Kecepatan**")
            speed_laden = st.number_input("Speed laden (knot)", min_value=1.0, value=12.5, step=0.5, key="voy_speed_laden")
            speed_ballast = st.number_input("Speed ballast (knot)", min_value=1.0, value=13.0, step=0.5, key="voy_speed_ballast")
        with c2:
            st.markdown("**Konsumsi bahan bakar utama, mis. IFO/VLSFO (MT/hari)**")
            ifo_laden = st.number_input("Saat laden", min_value=0.0, value=28.0, step=1.0, key="voy_ifo_laden")
            ifo_ballast = st.number_input("Saat ballast", min_value=0.0, value=26.0, step=1.0, key="voy_ifo_ballast")
            ifo_port = st.number_input("Saat di pelabuhan (idle)", min_value=0.0, value=3.0, step=0.5, key="voy_ifo_port")
        with c3:
            st.markdown("**Konsumsi bahan bakar sekunder, mis. MDO/MGO (MT/hari)**")
            mdo_sea = st.number_input("Saat berlayar (laden & ballast)", min_value=0.0, value=1.0, step=0.5, key="voy_mdo_sea")
            mdo_port = st.number_input("Saat di pelabuhan", min_value=0.0, value=2.0, step=0.5, key="voy_mdo_port")
        st.caption(
            "Kapal kecil domestik umumnya hanya pakai satu jenis bahan bakar (MDO/MGO/Solar) — "
            "kosongkan/nolkan grade pertama bila tidak berlaku, atau pakai preset di atas."
        )

    # ---- Sub-tab: Days & Port Costs ----
    with sub_days:
        st.markdown("**Hari**")
        c1, c2 = st.columns(2)
        with c1:
            load_days = st.number_input("Hari di load port", min_value=0.0, value=2.0, step=0.5, key="voy_load_days")
            disch_days = st.number_input("Hari di discharge port", min_value=0.0, value=2.0, step=0.5, key="voy_disch_days")
        with c2:
            canal_days = st.number_input("Hari transit kanal (jika ada)", min_value=0.0, value=0.0, step=0.5, key="voy_canal_days")
            other_days = st.number_input(
                "Hari tambahan lain (bunkering/waiting)", min_value=0.0, value=0.0, step=0.25, key="voy_other_days"
            )
        st.caption(
            "Loading/discharging rate cargo curah domestik (CPO, BBM, aspal, dll.) bervariasi "
            "tergantung fasilitas pelabuhan setempat — sesuaikan hari pelabuhan dengan "
            "pengalaman aktual di pelabuhan tersebut, bukan asumsi rate internasional."
        )

        st.markdown("**Biaya pelabuhan & lainnya**")
        use_pelindo = st.checkbox(
            "Gunakan rincian biaya pelabuhan gaya Indonesia (Pelindo/PNBP: labuh, tambat, pandu, tunda, dermaga/PBM)",
            value=is_domestic,
            key="voy_use_pelindo",
        )

        def pelindo_breakdown(label: str, key_prefix: str) -> float:
            with st.expander(f"Rincian biaya {label} (gaya Pelindo/PNBP)"):
                p1, p2, p3 = st.columns(3)
                with p1:
                    labuh = st.number_input(f"Labuh ({symbol})", min_value=0.0, value=0.0, key=f"{key_prefix}_labuh")
                    tambat = st.number_input(f"Tambat ({symbol})", min_value=0.0, value=0.0, key=f"{key_prefix}_tambat")
                with p2:
                    pandu = st.number_input(f"Pandu / pilotage ({symbol})", min_value=0.0, value=0.0, key=f"{key_prefix}_pandu")
                    tunda = st.number_input(f"Tunda / towage ({symbol})", min_value=0.0, value=0.0, key=f"{key_prefix}_tunda")
                with p3:
                    dermaga = st.number_input(f"Dermaga / PBM ({symbol})", min_value=0.0, value=0.0, key=f"{key_prefix}_dermaga")
                total = labuh + tambat + pandu + tunda + dermaga
                st.caption(f"Total {label}: {symbol} {total:,.0f} (isi 0 pada komponen yang tidak berlaku)")
            return total

        if use_pelindo:
            load_port_cost = pelindo_breakdown("load port", "voy_load")
            disch_port_cost = pelindo_breakdown("discharge port", "voy_disch")
        else:
            c1, c2 = st.columns(2)
            with c1:
                load_port_cost = st.number_input(
                    f"Biaya di load port ({symbol})", min_value=0.0, value=d(25_000.0), step=500.0, key="voy_load_cost"
                )
            with c2:
                disch_port_cost = st.number_input(
                    f"Biaya di discharge port ({symbol})", min_value=0.0, value=d(25_000.0), step=500.0, key="voy_disch_cost"
                )

        c1, c2 = st.columns(2)
        with c1:
            canal_cost = st.number_input(
                f"Biaya kanal / lain-lain ({symbol})", min_value=0.0, value=d(0.0), step=500.0, key="voy_canal_cost"
            )
        with c2:
            opex_day = st.number_input(
                f"OPEX ({symbol}/hari) — opsional", min_value=0.0, value=d(0.0), step=100.0, key="voy_opex_day"
            )
        include_opex = st.checkbox("Sertakan OPEX/hari dalam TCE (extended TCE)", value=False, key="voy_include_opex")

    # ---- Sub-tab: Bunker price ----
    with sub_bunker:
        c1, c2 = st.columns(2)
        with c1:
            ifo_price = st.number_input(
                f"Harga bahan bakar utama, mis. IFO/VLSFO ({symbol}/MT)", min_value=0.0, value=d(550.0), step=10.0, key="voy_ifo_price"
            )
        with c2:
            mdo_price = st.number_input(
                f"Harga bahan bakar sekunder, mis. MDO/MGO ({symbol}/MT)", min_value=0.0, value=d(750.0), step=10.0, key="voy_mdo_price"
            )
        st.caption(
            "Untuk bunker domestik yang biasa dibeli per liter/kiloliter (mis. dari Pertamina "
            "Patra Niaga), konversikan dulu ke basis per MT sebelum diisi di sini."
        )

    st.markdown("---")
    hire_rate_compare = st.number_input(
        f"Bandingkan dengan Time Charter hire rate ({symbol}/hari) — opsional, isi 0 jika tidak perlu",
        min_value=0.0,
        value=d(0.0),
        step=500.0,
        key="voy_hire_compare",
    )

    # -------------------------------------------------------------------
    # PERHITUNGAN (currency-agnostic — mengikuti satuan yang diisi user)
    # -------------------------------------------------------------------
    sea_days_laden = laden_distance / (speed_laden * 24) if speed_laden > 0 else 0
    sea_days_ballast = (ballast_distance / (speed_ballast * 24)) if (has_ballast and speed_ballast > 0) else 0
    total_sea_days = sea_days_laden + sea_days_ballast
    total_port_days = load_days + disch_days
    total_voyage_days = total_sea_days + total_port_days + canal_days + other_days

    ifo_qty = (sea_days_laden * ifo_laden) + (sea_days_ballast * ifo_ballast) + (total_port_days * ifo_port)
    mdo_qty = (total_sea_days * mdo_sea) + (total_port_days * mdo_port)
    bunker_cost = (ifo_qty * ifo_price) + (mdo_qty * mdo_price)

    total_commission_pct = addr_comm + broker_comm
    commission_amount = gross_freight * total_commission_pct / 100
    net_freight = gross_freight - commission_amount

    port_costs_total = load_port_cost + disch_port_cost
    other_costs_total = canal_cost
    total_voyage_cost = bunker_cost + port_costs_total + other_costs_total

    net_voyage_result = net_freight - total_voyage_cost
    tce_base = net_voyage_result / total_voyage_days if total_voyage_days > 0 else 0
    tce = tce_base + opex_day if include_opex else tce_base

    # -------------------------------------------------------------------
    # HASIL
    # -------------------------------------------------------------------
    st.markdown("## 📊 Hasil Voyage Estimate")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Voyage Days", f"{total_voyage_days:,.2f} hari")
    k2.metric("Net Freight", f"{symbol} {net_freight:,.0f}")
    k3.metric("Total Voyage Cost", f"{symbol} {total_voyage_cost:,.0f}")
    k4.metric(
        "TCE" + (" (extended, +OPEX)" if include_opex else ""),
        f"{symbol} {tce:,.0f} /hari",
        (f"{tce - hire_rate_compare:,.0f} vs TC hire" if hire_rate_compare > 0 else None),
    )

    st.markdown("### 🧮 Rincian Perhitungan")

    col_a, col_b = st.columns([1.1, 1])

    with col_a:
        breakdown_rows = [
            ("Gross Freight", f"{symbol} {gross_freight:,.0f}"),
            (f"- Komisi ({total_commission_pct:.2f}%)", f"{symbol} {commission_amount:,.0f}"),
            ("= Net Freight", f"{symbol} {net_freight:,.0f}"),
            ("- Biaya Bunker (2 grade)", f"{symbol} {bunker_cost:,.0f}"),
            ("- Biaya Pelabuhan (Load + Discharge)", f"{symbol} {port_costs_total:,.0f}"),
            ("- Biaya Kanal/Lain-lain", f"{symbol} {other_costs_total:,.0f}"),
            ("= Net Voyage Result", f"{symbol} {net_voyage_result:,.0f}"),
            ("÷ Total Voyage Days", f"{total_voyage_days:,.2f} hari"),
            ("= TCE dasar (per hari)", f"{symbol} {tce_base:,.0f}"),
        ]
        if include_opex:
            breakdown_rows.append(("+ OPEX/hari", f"{symbol} {opex_day:,.0f}"))
            breakdown_rows.append(("= TCE extended (per hari)", f"{symbol} {tce:,.0f}"))
        breakdown = pd.DataFrame(breakdown_rows, columns=["Komponen", "Nilai"])
        st.dataframe(breakdown, hide_index=True, use_container_width=True)

        st.markdown("**Rincian durasi & konsumsi**")
        detail = pd.DataFrame(
            {
                "Item": [
                    "Sea days (laden)",
                    "Sea days (ballast)",
                    "Port days (load+discharge)",
                    "Canal days",
                    "Hari lain (bunkering/waiting)",
                    "Konsumsi bahan bakar utama total",
                    "Konsumsi bahan bakar sekunder total",
                ],
                "Nilai": [
                    f"{sea_days_laden:,.2f} hari",
                    f"{sea_days_ballast:,.2f} hari",
                    f"{total_port_days:,.2f} hari",
                    f"{canal_days:,.2f} hari",
                    f"{other_days:,.2f} hari",
                    f"{ifo_qty:,.1f} MT",
                    f"{mdo_qty:,.1f} MT",
                ],
            }
        )
        st.dataframe(detail, hide_index=True, use_container_width=True)

    with col_b:
        fig = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "relative", "total"],
                x=["Gross Freight", "Komisi", "Bunker", "Biaya Pelabuhan", "Kanal/Lain", "Net Result"],
                y=[
                    gross_freight,
                    -commission_amount,
                    -bunker_cost,
                    -port_costs_total,
                    -other_costs_total,
                    0,
                ],
                connector={"line": {"color": "rgba(120,120,120,0.4)"}},
                decreasing={"marker": {"color": "#D9534F"}},
                increasing={"marker": {"color": "#5CB85C"}},
                totals={"marker": {"color": "#0B5394"}},
            )
        )
        fig.update_layout(
            title=f"Dari Gross Freight ke Net Voyage Result ({symbol})",
            height=430,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    if hire_rate_compare > 0:
        diff = tce - hire_rate_compare
        total_diff = diff * total_voyage_days
        if diff >= 0:
            st.success(
                f"✅ TCE **{symbol} {tce:,.0f}/hari** lebih tinggi **{symbol} {diff:,.0f}/hari** dibanding "
                f"TC hire (**{symbol} {hire_rate_compare:,.0f}/hari**). Estimasi selisih hasil selama "
                f"voyage: **{symbol} {total_diff:,.0f}**."
            )
        else:
            st.error(
                f"⚠️ TCE **{symbol} {tce:,.0f}/hari** lebih rendah **{symbol} {abs(diff):,.0f}/hari** dibanding "
                f"TC hire (**{symbol} {hire_rate_compare:,.0f}/hari**). Estimasi selisih hasil selama "
                f"voyage: **{symbol} {total_diff:,.0f}**."
            )

    # -------------------------------------------------------------------
    # REVERSE CALCULATOR: FREIGHT RATE MINIMUM UNTUK TARGET TCE
    # -------------------------------------------------------------------
    with st.expander("🎯 Hitung mundur: Freight rate minimum untuk target TCE"):
        target_tce = st.number_input(
            f"Target TCE ({symbol}/hari)", min_value=0.0, value=d(15_000.0), step=500.0, key="voy_target_tce"
        )
        if total_voyage_days > 0 and cargo_qty > 0 and total_commission_pct < 100:
            target_tce_base = target_tce - opex_day if include_opex else target_tce
            required_net_result = target_tce_base * total_voyage_days
            required_net_freight = required_net_result + total_voyage_cost
            required_gross_freight = required_net_freight / (1 - total_commission_pct / 100)
            required_rate_per_mt = required_gross_freight / cargo_qty
            st.info(
                f"Untuk mencapai TCE **{symbol} {target_tce:,.0f}/hari**, dibutuhkan freight rate "
                f"minimum **{symbol} {required_rate_per_mt:,.2f}/MT** (setara lumpsum "
                f"**{symbol} {required_gross_freight:,.0f}**), dengan asumsi biaya voyage & komisi "
                "tetap sama seperti input di atas."
            )
        else:
            st.warning("Lengkapi data voyage days, cargo quantity, dan komisi (<100%) terlebih dahulu.")

    st.caption(
        "Formula: Handybulk — Voyage Estimation (Time at Sea, Port Days & TCE), TCE — Time Charter Equivalent. "
        "Extended TCE (+OPEX/hari): The Signal Group — TCE Benchmarking: A Tanker Operator's Guide; "
        "Heisenberg Shipping — Time Charter Equivalent (TCE)."
    )

# ==============================================================================
# TAB 3 — LAYTIME & DEMURRAGE/DESPATCH CALCULATOR
# ==============================================================================
with tab_lay:
    st.subheader("⏱️ Laytime & Demurrage/Despatch Calculator")
    st.markdown(
        """
**Laytime** adalah waktu yang dialokasikan ke Charterer untuk cargo operations.
Jika waktu terpakai **melebihi** allowed laytime → kapal *on demurrage* (Owner
dibayar). Jika **lebih cepat** → *despatch* (Owner membayar Charterer), bila
charter party memberi hak despatch — konvensi umum: despatch rate = 50% demurrage rate.
Berlaku universal untuk fixture domestik maupun internasional.
        """
    )

    lay_currency = st.radio(
        "Mata uang", ["USD ($)", "IDR (Rp)"], horizontal=True, key="lay_currency"
    )
    lay_symbol = "$" if lay_currency.startswith("USD") else "Rp"
    lay_default_demurrage = 25_000.0 if lay_symbol == "$" else 375_000_000.0

    st.markdown("##### 1) Allowed Laytime")
    lay_mode = st.radio(
        "Metode input allowed laytime",
        ["Input langsung (hari)", "Hitung dari Cargo Qty ÷ Rate"],
        horizontal=True,
        key="lay_mode",
    )
    if lay_mode == "Input langsung (hari)":
        allowed_days = st.number_input(
            "Allowed Laytime (hari)", min_value=0.0, value=3.0, step=0.25, key="lay_allowed_days"
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            lay_qty = st.number_input("Cargo Quantity (MT)", min_value=1.0, value=80_000.0, step=1_000.0, key="lay_qty")
        with c2:
            lay_rate = st.number_input(
                "Loading/Discharging Rate (MT/hari)", min_value=1.0, value=20_000.0, step=500.0, key="lay_rate"
            )
        allowed_days = lay_qty / lay_rate
        st.caption(f"Allowed laytime = {lay_qty:,.0f} MT ÷ {lay_rate:,.0f} MT/hari = **{allowed_days:.3f} hari**")

    st.markdown("##### 2) Waktu Terpakai (Time Used)")
    used_mode = st.radio(
        "Metode input waktu terpakai",
        ["Input langsung (jam)", "Hitung dari NOR & waktu selesai"],
        horizontal=True,
        key="used_mode",
    )
    if used_mode == "Input langsung (jam)":
        used_hours = st.number_input("Time Used (jam)", min_value=0.0, value=70.0, step=0.5, key="lay_used_hours")
    else:
        c1, c2 = st.columns(2)
        with c1:
            nor_date = st.date_input("Tanggal NOR ditender", value=dt.date.today(), key="nor_date")
            nor_time = st.time_input("Jam NOR ditender", value=dt.time(8, 0), key="nor_time")
            turn_time = st.number_input(
                "Turn time setelah NOR (jam)", min_value=0.0, value=6.0, step=0.5, key="turn_time",
                help="Umumnya 6 jam setelah NOR pada banyak bentuk voyage charter tanker — periksa klausul NOR pada charter party spesifik Anda.",
            )
        with c2:
            comp_date = st.date_input("Tanggal cargo ops selesai", value=dt.date.today(), key="comp_date")
            comp_time = st.time_input("Jam cargo ops selesai", value=dt.time(18, 0), key="comp_time")
            excepted_hours = st.number_input(
                "Excepted time (jam) — cuaca/SHEX/dll.", min_value=0.0, value=0.0, step=0.5, key="excepted_hours",
                help="Jam yang dikecualikan dari laytime menurut wording charter party (SHINC/SHEX/EIU/UU); "
                "termasuk cuaca buruk/swell/monsoon yang lazim di banyak pelabuhan Indonesia.",
            )

        nor_dt = dt.datetime.combine(nor_date, nor_time)
        commence_dt = nor_dt + dt.timedelta(hours=turn_time)
        completion_dt = dt.datetime.combine(comp_date, comp_time)
        raw_hours = max((completion_dt - commence_dt).total_seconds() / 3600.0, 0.0)
        used_hours = max(raw_hours - excepted_hours, 0.0)

        st.caption(
            f"Laytime commences: **{commence_dt:%d %b %Y %H:%M}** · "
            f"Selesai: **{completion_dt:%d %b %Y %H:%M}** · "
            f"Waktu kotor: {raw_hours:.2f} jam · Excepted: {excepted_hours:.2f} jam · "
            f"**Time used: {used_hours:.2f} jam**"
        )

    st.markdown("##### 3) Demurrage / Despatch Rate")
    c1, c2 = st.columns(2)
    with c1:
        demurrage_rate = st.number_input(
            f"Demurrage Rate ({lay_symbol}/hari, PDPR)", min_value=0.0, value=lay_default_demurrage, step=500.0, key="demurrage_rate"
        )
    with c2:
        despatch_rate = st.number_input(
            f"Despatch Rate ({lay_symbol}/hari)",
            min_value=0.0,
            value=demurrage_rate / 2,
            step=500.0,
            key="despatch_rate",
            help="Konvensi umum industri: 50% dari demurrage rate — dapat diubah sesuai charter party.",
        )

    allowed_hours = allowed_days * 24.0
    diff_hours = used_hours - allowed_hours

    st.markdown("##### Hasil")
    r1, r2, r3 = st.columns(3)
    r1.metric("Allowed Laytime", f"{allowed_hours:.2f} jam ({allowed_hours/24:.3f} hari)")
    r2.metric("Time Used", f"{used_hours:.2f} jam ({used_hours/24:.3f} hari)")

    if diff_hours > 0:
        demurrage_days = diff_hours / 24.0
        demurrage_amt = demurrage_days * demurrage_rate
        r3.metric("Selisih", f"+{diff_hours:.2f} jam", delta=f"{demurrage_days:.3f} hari on demurrage")
        st.error(f"🔴 **ON DEMURRAGE** — Demurrage payable: **{lay_symbol} {demurrage_amt:,.2f}**")
    elif diff_hours < 0:
        despatch_days = abs(diff_hours) / 24.0
        despatch_amt = despatch_days * despatch_rate
        r3.metric("Selisih", f"{diff_hours:.2f} jam", delta=f"{despatch_days:.3f} hari despatch")
        st.success(f"🟢 **DESPATCH DUE** — Despatch payable: **{lay_symbol} {despatch_amt:,.2f}**")
    else:
        r3.metric("Selisih", "0.00 jam")
        st.info("⚪ Laytime terpakai persis sama dengan allowed laytime — tidak ada demurrage/despatch.")

    st.caption(
        "Metodologi: Handybulk — Laytime, Calculation of Demurrage, Laytime/Demurrage/Despatch Explained. "
        "Konvensi despatch 50%: Heisenberg Shipping — Online Laytime Calculator Tool."
    )

st.markdown("---")
st.caption(
    "Tanker Chartering Toolkit (Merged, disesuaikan pasar Indonesia) • Alat bantu estimasi, "
    "bukan pengganti perhitungan chartering resmi. Selalu verifikasi ulang sebelum fixture. "
    "Dibangun dengan Streamlit."
)
