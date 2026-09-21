"""
Tanker Chartering Toolkit
=========================
Tiga modul dalam satu aplikasi Streamlit:

  1. Worldscale Freight Calculation   — konversi flat rate (WS100) + WS% menjadi freight USD.
  2. Voyage Estimate & TCE Calculator — freight, bunker, biaya pelabuhan, dan waktu voyage
                                        menjadi TCE, dengan toggle Domestik/Internasional
                                        dan toggle mata uang USD/IDR.
  3. Laytime & Demurrage/Despatch     — allowed laytime, waktu terpakai, demurrage/despatch.

Nama pelabuhan load/discharge diisi manual (diketik).
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

# Faktor skala internal untuk default nilai saat mata uang = IDR
# (hanya untuk mengisi angka awal input; tidak ditampilkan dan tidak memengaruhi kalkulasi).
DEFAULT_FX_IDR_PER_USD = 17_700.0

st.title("🛢️ Tanker Chartering Toolkit")
st.caption("Worldscale freight · Voyage estimate (TCE) · Laytime & demurrage/despatch")

tab_ws, tab_voy, tab_lay = st.tabs(
    [
        "⚓ Worldscale Freight",
        "🧮 Voyage Estimate (TCE)",
        "⏱️ Laytime & Demurrage",
    ]
)

# ==============================================================================
# TAB 1 — WORLDSCALE FREIGHT CALCULATION
# ==============================================================================
with tab_ws:
    st.subheader("⚓ Worldscale Freight Calculation")
    st.markdown(
        """
**Worldscale (Worldwide Tanker Nominal Freight Scale)** adalah sistem indeks acuan atau daftar tarif standar yang digunakan untuk menentukan biaya pengangkutan kargo minyak dan produk turunannya menggunakan kapal tanker. Worldscale adalah tabel referensi tarif dasar (*flat rate*) per ton untuk ratusan ribu rute pelayaran di seluruh dunia. Tarif dasar dihitung berdasarkan asumsi kapal standar berukuran 75.000 deadweight tonnage (DWT), kecepatan 14,5 knot, biaya operasional harian tetap (sebesar $12.000), serta estimasi biaya bahan bakar (bunker) dan pelabuhan. Negosiasi harga antara pemilik kapal (*shipowner*) dan penyewa (*charterer*) dilakukan berdasarkan persentase dari tarif dasar Worldscale (disebut *WS points*). Contoh: WS100 berarti biaya sewa persis 100% dari tarif dasar yang tercantum. Jika pasar sedang tinggi, tarif bisa disepakati pada WS150 (150% dari tarif dasar), atau WS80 (80%) jika pasar sedang turun.
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
            help="Masukkan flat rate dari tabel Worldscale berlisensi Anda untuk rute yang sesungguhnya.",
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

# ==============================================================================
# TAB 2 — VOYAGE ESTIMATE / TCE CALCULATOR
# ==============================================================================
with tab_voy:
    st.subheader("🧮 Voyage Estimate & TCE Calculator")
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
                "dan dioperasikan perusahaan pelayaran nasional."
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

    def d(usd_value: float) -> float:
        """Skala nilai default USD ke IDR (ilustrasi) bila mata uang = IDR."""
        return usd_value if symbol == "$" else round(usd_value * DEFAULT_FX_IDR_PER_USD, -3)

    sub_cargo, sub_speed, sub_days, sub_bunker = st.tabs(
        ["🗺️ Voyage & Freight", "🚢 Kecepatan & Konsumsi", "⚓ Hari & Biaya Pelabuhan", "⛽ Harga Bunker"]
    )

    # ---- Sub-tab: Voyage & Freight ----
    with sub_cargo:
        c1, c2 = st.columns(2)
        with c1:
            load_port = st.text_input(
                "Pelabuhan muat (load port)", key="voy_load_port", placeholder="Ketik nama pelabuhan"
            ).strip()
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
            discharge_port = st.text_input(
                "Pelabuhan bongkar (discharge port)", key="voy_disch_port", placeholder="Ketik nama pelabuhan"
            ).strip()

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
                        "Anda diset ke IDR, konversikan manual memakai kurs terkini."
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
    total_fuel_qty = ifo_qty + mdo_qty
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
    if load_port or discharge_port:
        st.caption(f"Rute: **{load_port or '-'}** → **{discharge_port or '-'}**")

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
            ("- Biaya Bunker", f"{symbol} {bunker_cost:,.0f}"),
            ("- Biaya Pelabuhan (Load + Discharge)", f"{symbol} {port_costs_total:,.0f}"),
            ("- Biaya Lain-lain", f"{symbol} {other_costs_total:,.0f}"),
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
                    "Hari lain (bunkering/waiting)",
                    "Konsumsi bahan bakar",
                ],
                "Nilai": [
                    f"{sea_days_laden:,.2f} hari",
                    f"{sea_days_ballast:,.2f} hari",
                    f"{total_port_days:,.2f} hari",
                    f"{other_days:,.2f} hari",
                    f"{total_fuel_qty:,.1f} MT",
                ],
            }
        )
        st.dataframe(detail, hide_index=True, use_container_width=True)

    with col_b:
        fig = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "relative", "total"],
                x=["Gross Freight", "Komisi", "Bunker", "Biaya Pelabuhan", "Lain-lain", "Net Result"],
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
