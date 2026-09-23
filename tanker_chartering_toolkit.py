# ==============================================================================
# TAB 3 — LAYTIME & DEMURRAGE CALCULATOR
# ==============================================================================
with tab_lay:
    st.subheader("⏱️ Laytime & Demurrage Calculation")
    st.info(
        "ℹ️ **Tanker charter parties do not pay despatch.** Unlike dry bulk, jika laytime "
        "tidak habis terpakai, owner tidak membayar kompensasi apa pun kepada charterer. "
        "Kalkulator ini hanya menghitung demurrage."
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

    st.markdown("##### 3) Demurrage Rate")
    demurrage_rate = st.number_input(
        f"Demurrage Rate ({lay_symbol}/hari, PDPR)", min_value=0.0, value=lay_default_demurrage, step=500.0, key="demurrage_rate"
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
    else:
        # diff_hours <= 0 → tidak ada despatch di tanker
        saved_hours = abs(diff_hours) if diff_hours < 0 else 0.0
        r3.metric("Selisih", f"{diff_hours:.2f} jam", delta=f"{saved_hours:.2f} jam saved")
        st.success(
            f"🟢 **NO DEMURRAGE** — Laytime masih tersisa **{saved_hours:.2f} jam**. "
            f"Catatan: dalam tanker charter party, **despatch tidak dibayar** ke charterer."
        )
