from gentool_menu.portage_io import *

def generate_kconfig(state: dict, kpath: Path) -> None:
    by_cat = {}
    for p in state["packages"]: by_cat.setdefault(p["cat"], []).append(p)
    L = ['mainmenu "Gentool Portage Configuration Manager"', "", 'menu "1. USE Flags (package.use)"']
    for cat in sorted(by_cat):
        pkgs = [p for p in by_cat[cat] if p["flags"]]
        if not pkgs: continue
        mod = sum(1 for p in pkgs if p["use_mod"])
        L.append(f'menu "{cat} ({len(pkgs)} pkgs' + (f', {mod} modified)"' if mod else ')"'))
        for p in pkgs:
            L.append(f'menu "{p["name"]}{" [mod]" if p["use_mod"] else ""} ({p["cp"]})"')
            for i in p["flags"]: L += [f'config {i["sym"]}', f'    bool "{i["flag"]}"', f'    default {"y" if i["effective"] else "n"}', ""]
            L += ["endmenu", ""]
        L += ["endmenu", ""]
    L += ["endmenu", "", 'menu "2. Accept Keywords (package.accept_keywords)"']
    for cat in sorted(by_cat):
        pkgs = by_cat[cat]; mod = sum(1 for p in pkgs if p["kw_t"] or p["kw_l"])
        L.append(f'menu "{cat} ({len(pkgs)} pkgs' + (f', {mod} keyworded)"' if mod else ')"'))
        for p in pkgs:
            tag = " [kw]" if (p["kw_t"] or p["kw_l"]) else ""
            L += [f'menu "{p["name"]}{tag} ({p["cp"]})"', f'config {p["sym_kt"]}', '    bool "Accept ~amd64"', f'    default {"y" if p["kw_t"] else "n"}', "", f'config {p["sym_kl"]}', '    bool "Accept **"', f'    default {"y" if p["kw_l"] else "n"}', "", "endmenu", ""]
        L += ["endmenu", ""]
    L += ["endmenu", "", 'menu "3. Package Masking (package.mask)"']
    for cat in sorted(by_cat):
        pkgs = by_cat[cat]; mod = sum(1 for p in pkgs if p["mask_mode"] != "NONE")
        L.append(f'menu "{cat} ({len(pkgs)} pkgs' + (f', {mod} masked)"' if mod else ')"'))
        for p in pkgs:
            tag = f" [{p['mask_atom']}]" if p["mask_atom"] else ""
            ds = {"NONE": p["sym_mn"], "ALL": p["sym_ma"], "EQ": p["sym_me"], "FWD": p["sym_mf"]}[p["mask_mode"]]
            el = p["mask_atom"] if p["mask_mode"] == "EQ" else f"={p['cpv']}"
            fl = p["mask_atom"] if p["mask_mode"] == "FWD" else f">={p['cpv']}"
            L += [f'menu "{p["name"]}{tag} ({p["cp"]})"', "choice", f'    prompt "Mask {p["cp"]}"', f"    default {ds}", f'config {p["sym_mn"]}', '    bool "Unmasked"', f'config {p["sym_ma"]}', f'    bool "All ({p["cp"]})"', f'config {p["sym_me"]}', f'    bool "Exact ({el})"', f'config {p["sym_mf"]}', f'    bool "Forward ({fl})"', "endchoice", "", "endmenu", ""]
        L += ["endmenu", ""]
    L += ["endmenu", "", 'menu "4. Package Environments (package.env)"']
    for cat in sorted(by_cat):
        pkgs = by_cat[cat]; mod = sum(1 for p in pkgs if p["has_env"])
        L.append(f'menu "{cat} ({len(pkgs)} pkgs' + (f', {mod} assigned)"' if mod else ')"'))
        for p in pkgs:
            tag = " [env]" if p["has_env"] else ""
            L.append(f'menu "{p["name"]}{tag} ({p["cp"]})"')
            for e in p["envs"]: L += [f'config {e["sym"]}', f'    bool "Use {e["name"]}"', f'    default {"y" if e["initial"] else "n"}', ""]
            L += ["endmenu", ""]
        L += ["endmenu", ""]
    L += ["endmenu", "", 'menu "5. Environment Profiles (/etc/portage/env)"', 'menu "Edit Existing /etc/portage/env Files"']
    for ef in state["ed_envs"]:
        L.append(f'menu "{ef["fname"]}"')
        for vf in ef["vars"]:
            esc = vf["initial"].replace("\\", "\\\\").replace('"', '\\"')
            L += [f'config {vf["sym"]}', f'    string "{vf["key"]}"', f'    default "{esc}"', ""]
        L += [f'config {ef["sym_del"]}', f'    bool "Delete {ef["fname"]}"', "    default n", "", "endmenu", ""]
    L += ["endmenu", "", 'menu "Create New /etc/portage/env Profile"', 'config ENEW_FILENAME', '    string "New filename"', '    default ""', ""]
    for k in ["CFLAGS", "CXXFLAGS", "LDFLAGS", "MAKEOPTS", "FEATURES"]: L += [f'config ENEW_{k}', f'    string "{k}"', '    default ""', ""]
    L += ["endmenu", "", 'menu "Quick Presets"']
    for i in state["env_items"]: L += [f'config {i["sym"]}', f'    bool "{i["fname"]} - {i["desc"]}"', f'default {"y" if i["initial"] else "n"}', ""]
    L += ["endmenu", "", "endmenu", "", 'menu "6. Global make.conf (USE & FEATURES)"', 'menu "Global USE Flags (make.conf USE=...)"']
    for i in state["g_use"]: L += [f'config {i["sym"]}', f'    bool "{i["flag"]}"', f'    default {"y" if i["initial"] else "n"}', ""]
    L += ["endmenu", "", 'menu "Global FEATURES (make.conf FEATURES=...)"']
    for i in state["g_feat"]: L += [f'config {i["sym"]}', f'    bool "{i["feature"]} - {i["desc"]}"', f'    default {"y" if i["initial"] else "n"}', ""]
    L += ["endmenu", "", "endmenu", ""]
    kpath.write_text("\n".join(L), encoding="utf-8")

def write_one(target: Path, line: str | None) -> None:
    comments = [r for r in target.read_text(encoding="utf-8").splitlines() if r.strip().startswith("#")] if target.is_file() else []
    if not line:
        if comments:
            target.write_text("\n".join(comments) + "\n", encoding="utf-8")
        elif target.is_file():
            target.unlink()
            try:
                target.parent.rmdir()
            except OSError:
                pass
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(comments + [line]) + "\n", encoding="utf-8")

def apply_all_changes(state: dict, kconf: kconfiglib.Kconfig) -> None:
    is_root = os.geteuid() == 0
    base = PORTAGE_DIR if is_root else (Path.cwd() / "portage-preview")
    changed = 0

    nu, u_chg = dict(state["exp_use"]), False
    for i in state["g_use"]:
        s = kconf.syms.get(i["sym"])
        if s and (s.str_value == "y") != i["initial"]:
            u_chg, nu[i["flag"]] = True, (s.str_value == "y")

    nf, f_chg = dict(state["exp_feat"]), False
    for i in state["g_feat"]:
        s = kconf.syms.get(i["sym"])
        if s and (s.str_value == "y") != i["initial"]:
            f_chg, nf[i["feature"]] = True, (s.str_value == "y")

    if u_chg or f_chg:
        changed += 1
        mc = state["mc_text"]
        if u_chg:
            mc = update_make_conf_var(mc, "USE", [f"{'' if nu[k] else '-'}{k}" for k in sorted(nu)], False)
            print("  [make.conf] Updated USE")
        if f_chg:
            mc = update_make_conf_var(mc, "FEATURES", [f"{'' if nf[k] else '-'}{k}" for k in sorted(nf)], True)
            print("  [make.conf] Updated FEATURES")
        out_mc = state["mc_file"] if is_root else (base / "make.conf")
        out_mc.parent.mkdir(parents=True, exist_ok=True)
        out_mc.write_text(mc, encoding="utf-8")

    for ef in state["ed_envs"]:
        t_f = base / "env" / ef["fname"]
        if kconf.syms.get(ef["sym_del"]) and kconf.syms[ef["sym_del"]].str_value == "y":
            changed += 1
            t_f.unlink(missing_ok=True)
            print(f"  [env] Deleted {t_f}")
            continue
        nv, vc = {}, False
        for vf in ef["vars"]:
            sv = kconf.syms.get(vf["sym"])
            val = sv.str_value if sv else vf["initial"]
            if val != vf["initial"]:
                vc = True
            if val.strip():
                nv[vf["key"]] = val
        if vc:
            changed += 1
            t_f.parent.mkdir(parents=True, exist_ok=True)
            t_f.write_text(render_env_vars(nv), encoding="utf-8")
            print(f"  [env] Updated {t_f}")

    nfn = kconf.syms["ENEW_FILENAME"].str_value.strip() if "ENEW_FILENAME" in kconf.syms else ""
    if nfn:
        nvm = {k: kconf.syms[f"ENEW_{k}"].str_value.strip() for k in ["CFLAGS", "CXXFLAGS", "LDFLAGS", "MAKEOPTS", "FEATURES"] if f"ENEW_{k}" in kconf.syms and kconf.syms[f"ENEW_{k}"].str_value.strip()}
        if nvm:
            changed += 1
            t_f = base / "env" / Path(nfn).name
            t_f.parent.mkdir(parents=True, exist_ok=True)
            t_f.write_text(render_env_vars(nvm), encoding="utf-8")
            print(f"  [env] Created {t_f}")

    for i in state["env_items"]:
        s = kconf.syms.get(i["sym"])
        if s and (s.str_value == "y") != i["initial"]:
            changed += 1
            t = base / "env" / i["fname"]
            if s.str_value == "y":
                t.parent.mkdir(parents=True, exist_ok=True)
                t.write_text(i["body"] + "\n", encoding="utf-8")
                print(f"  [env] Created {t}")
            else:
                t.unlink(missing_ok=True)
                print(f"  [env] Removed {t}")

    for p in state["packages"]:
        cp, cat, name = p["cp"], p["cat"], p["name"]
        uchg, duse = False, {}
        for i in p["flags"]:
            s = kconf.syms.get(i["sym"])
            val = (s.str_value == "y") if s else i["effective"]
            if val != i["effective"]:
                uchg = True
            if val != i["installed"]:
                duse[i["flag"]] = val
        if uchg:
            changed += 1
            t = base / "package.use" / cat / name
            write_one(t, f"{cp} {' '.join(f'{'' if duse[k] else '-'}{k}' for k in sorted(duse))}" if duse else None)
            print(f"  [package.use] Updated {t}")

        st, sl = kconf.syms.get(p["sym_kt"]), kconf.syms.get(p["sym_kl"])
        nt = (st.str_value == "y") if st else p["kw_t"]
        nl = (sl.str_value == "y") if sl else p["kw_l"]
        if nt != p["kw_t"] or nl != p["kw_l"]:
            changed += 1
            kws = (["~amd64"] if nt else []) + (["**"] if nl else [])
            t = base / "package.accept_keywords" / cat / name
            write_one(t, f"{cp} {' '.join(kws)}" if kws else None)
            print(f"  [package.accept_keywords] Updated {t}")

        nm = next((mk for mk, sk in [("ALL", "sym_ma"), ("EQ", "sym_me"), ("FWD", "sym_mf")] if kconf.syms.get(p[sk]) and kconf.syms[p[sk]].str_value == "y"), "NONE")
        if nm != p["mask_mode"]:
            changed += 1
            t = base / "package.mask" / cat / name
            na = None if nm == "NONE" else (cp if nm == "ALL" else ((p["mask_atom"] if p["mask_mode"] == "EQ" else f"={p['cpv']}") if nm == "EQ" else (p["mask_atom"] if p["mask_mode"] == "FWD" else f">={p['cpv']}")))
            write_one(t, na)
            print(f"  [package.mask] Updated {t} -> {na or 'unmasked'}")

        echg, aenvs = False, []
        for e in p["envs"]:
            s = kconf.syms.get(e["sym"])
            val = (s.str_value == "y") if s else e["initial"]
            if val != e["initial"]:
                echg = True
            if val:
                aenvs.append(e["name"])
        if echg:
            changed += 1
            t = base / "package.env" / cat / name
            write_one(t, f"{cp} {' '.join(sorted(aenvs))}" if aenvs else None)
            print(f"  [package.env] Updated {t}")

    print("\nNo changes made." if changed == 0 else "\nSaved cleanly. Run 'emerge -auDN @world' to apply.")

def main() -> None:
    print("Scanning installed packages and /etc/portage...")
    state = collect_portage_state()
    if not state["packages"]:
        sys.exit("No installed packages found.")
    with tempfile.TemporaryDirectory(prefix="gentool-menu-") as tmp:
        kp, cp = Path(tmp) / "Kconfig", Path(tmp) / ".config"
        generate_kconfig(state, kp)
        os.environ["KCONFIG_CONFIG"] = str(cp)
        kc = kconfiglib.Kconfig(str(kp))
        menuconfig.menuconfig(kc)
        if cp.is_file():
            kc.load_config(str(cp))
            apply_all_changes(state, kc)
        else:
            print("\nExited without saving.")

if __name__ == "__main__":
    main()
