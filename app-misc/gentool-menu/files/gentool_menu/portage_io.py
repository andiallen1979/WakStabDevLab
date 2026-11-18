import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import portage
except ImportError:
    sys.exit("Error: Gentoo 'portage' Python module not found.")

import kconfiglib
import menuconfig

PORTAGE_DIR = Path("/etc/portage")
MAKE_CONF_PATH = PORTAGE_DIR / "make.conf"
PKG_USE_BASE = PORTAGE_DIR / "package.use"
PKG_KW_BASE = PORTAGE_DIR / "package.accept_keywords"
PKG_MASK_BASE = PORTAGE_DIR / "package.mask"
PKG_ENV_BASE = PORTAGE_DIR / "package.env"
ENV_PROFILES_DIR = PORTAGE_DIR / "env"

STD_ENV_VARS = ["CFLAGS", "CXXFLAGS", "LDFLAGS", "MAKEOPTS", "FEATURES", "CC", "CXX"]

ENV_PRESETS = [
    ("NOLTO", 'CFLAGS="${CFLAGS} -fno-lto"\nCXXFLAGS="${CXXFLAGS} -fno-lto"\nLDFLAGS="${LDFLAGS} -fno-lto"', "Disable LTO (-fno-lto)"),
    ("O2_SAFE", 'CFLAGS="-O2 -pipe"\nCXXFLAGS="-O2 -pipe"', "Safe -O2 -pipe flags"),
    ("JOBS_1", 'MAKEOPTS="-j1"', "Limit build to single job (MAKEOPTS=-j1)"),
    ("NO_SANDBOX", 'FEATURES="${FEATURES} -sandbox -usersandbox"', "Disable Portage sandbox"),
    ("NO_TEST", 'FEATURES="${FEATURES} -test"', "Disable test phase"),
]

COMMON_GLOBAL_USE = [
    "X", "alsa", "bluetooth", "cups", "dbus", "dist-kernel", "elogind",
    "ffmpeg", "flac", "git", "gles2", "grub", "gtk", "icu", "ipv6",
    "jpeg", "lto", "mp3", "mp4", "networkmanager", "nls", "opengl",
    "pam", "pgo", "pipewire", "png", "policykit", "pulseaudio", "qt5",
    "qt6", "screencast", "seccomp", "ssl", "svg", "systemd", "truetype",
    "udev", "udisks", "unicode", "usb", "vaapi", "vdpau", "vulkan",
    "wayland", "webp", "x264", "x265", "zstd",
]

COMMON_FEATURES = [
    ("buildpkg", "Build binary packages (.gpkg.tar / .tbz2)"),
    ("buildpkg-live", "Build binary packages for live (-9999) ebuilds"),
    ("getbinpkg", "Fetch binary packages from configured binhosts"),
    ("binpkg-request-signature", "Require valid GPG signatures on binpkgs"),
    ("ccache", "Enable compiler caching via dev-util/ccache"),
    ("distcc", "Enable distributed compilation via sys-devel/distcc"),
    ("parallel-fetch", "Download sources in parallel while compiling"),
    ("parallel-install", "Install merged packages in parallel"),
    ("clean-logs", "Remove build logs after successful merges"),
    ("splitdebug", "Split debug symbols into /usr/lib/debug"),
    ("nodoc", "Skip installing documentation files"),
    ("noinfo", "Skip installing GNU info pages"),
    ("noman", "Skip installing manual pages"),
    ("sandbox", "Enable Portage filesystem sandbox"),
    ("usersandbox", "Drop privileges inside sandbox"),
    ("userpriv", "Build packages as unprivileged portage user"),
    ("test", "Run package test suites"),
]

def sanitize_symbol(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", raw).upper()

def extract_cp(atom_tok: str) -> str | None:
    clean, _, _ = re.sub(r"^[<>~=]+", "", atom_tok).partition("::")
    clean, _, _ = clean.partition(":")
    if "/" not in clean:
        return None
    try:
        return portage.dep_getkey(clean)
    except portage.exception.InvalidAtom:
        return portage.cpv_getkey(clean) or None

def read_make_conf_var(text: str, var_name: str) -> list[str]:
    pat = re.compile(rf'(?m)^\s*{re.escape(var_name)}\s*=\s*(["\'])(.*?)\1', re.DOTALL)
    out = []
    for m in pat.finditer(text):
        for tok in m.group(2).split():
            if tok not in (f"${{{var_name}}}", f"${var_name}"):
                out.append(tok)
    return out

def update_make_conf_var(text: str, var_name: str, tokens: list[str], self_ref: bool = False) -> str:
    prefix = f"${{{var_name}}} " if self_ref else ""
    line = f'{var_name}="{(prefix + " ".join(tokens)).strip()}"'
    pat = re.compile(rf'(?m)^\s*{re.escape(var_name)}\s*=\s*(["\'])(.*?)\1', re.DOTALL)
    matches = list(pat.finditer(text))
    if matches:
        res = text
        for m in reversed(matches[:-1]):
            res = res[:m.start()] + res[m.end():]
        last = list(pat.finditer(res))[-1]
        return res[:last.start()] + line + res[last.end():]
    sep = "" if (not text or text.endswith("\n")) else "\n"
    return f"{text}{sep}\n{line}\n"

def parse_env_vars(content: str) -> dict[str, str]:
    pat = re.compile(r'(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(["\'])(.*?)\2', re.DOTALL)
    return {m.group(1): m.group(3) for m in pat.finditer(content)}

def render_env_vars(var_map: dict[str, str]) -> str:
    lines = [f'{k}="{v}"' for k, v in var_map.items() if v.strip()]
    return "\n".join(lines) + ("\n" if lines else "")

def iter_cfg_lines(base_path: Path):
    if not base_path.exists():
        return
    files = [base_path] if base_path.is_file() else [p for p in sorted(base_path.rglob("*")) if p.is_file() and not p.name.startswith(".")]
    for f in files:
        for raw in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = raw.strip()
            if s and not s.startswith("#"):
                yield s.split()

def collect_portage_state() -> dict:
    vardb = portage.db[portage.root]["vartree"].dbapi
    settings = portage.config(clone=portage.settings)
    saved_use, saved_kw, saved_mask, saved_penv = {}, {}, {}, {}
    for toks in iter_cfg_lines(PKG_USE_BASE):
        cp = extract_cp(next(iter(toks))) if len(toks) >= 2 else None
        if cp:
            for t in toks[1:]: saved_use.setdefault(cp, {})[t.lstrip("-")] = not t.startswith("-")
    for toks in iter_cfg_lines(PKG_KW_BASE):
        cp = extract_cp(next(iter(toks)))
        if cp: saved_kw.setdefault(cp, set()).update(toks[1:] if len(toks) > 1 else ["~amd64"])
    for toks in iter_cfg_lines(PKG_MASK_BASE):
        ra = next(iter(toks)); cp = extract_cp(ra)
        if cp: saved_mask[cp] = ra
    for toks in iter_cfg_lines(PKG_ENV_BASE):
        cp = extract_cp(next(iter(toks))) if len(toks) >= 2 else None
        if cp: saved_penv.setdefault(cp, set()).update(toks[1:])
    env_profiles = {f.name: f.read_text(encoding="utf-8", errors="ignore") for f in sorted(ENV_PROFILES_DIR.iterdir()) if f.is_file()} if ENV_PROFILES_DIR.is_dir() else {}
    mc_file = MAKE_CONF_PATH
    if MAKE_CONF_PATH.is_dir():
        cands = sorted(f for f in MAKE_CONF_PATH.iterdir() if f.is_file() and not f.name.startswith("."))
        mc_file = cands[-1] if cands else (MAKE_CONF_PATH / "00-wakstab.conf")
    mc_text = mc_file.read_text(encoding="utf-8") if mc_file.is_file() else ""
    exp_use = {t.lstrip("-"): not t.startswith("-") for t in read_make_conf_var(mc_text, "USE")}
    act_use = set(settings.get("USE", "").split())
    g_use = [{"flag": f, "initial": exp_use.get(f, f in act_use), "sym": f"GUSE_{sanitize_symbol(f)}"} for f in sorted(set(COMMON_GLOBAL_USE) | set(exp_use))]
    exp_feat = {t.lstrip("-"): not t.startswith("-") for t in read_make_conf_var(mc_text, "FEATURES")}
    act_feat = set(settings.get("FEATURES", "").split())
    f_desc = dict(COMMON_FEATURES)
    g_feat = [{"feature": f, "desc": f_desc.get(f, "Custom feature"), "initial": exp_feat.get(f, f in act_feat), "sym": f"GFEAT_{sanitize_symbol(f)}"} for f in sorted(set(f_desc) | set(exp_feat))]
    presets = {f"gentool-{k.lower()}.conf": (b, d) for k, b, d in ENV_PRESETS}
    all_envs = sorted(set(env_profiles) | set(presets))
    inst_map, cp_ver, all_cps = {}, {}, set()
    skip = ("abi_", "kernel_", "elibc_", "userland_", "video_cards_", "input_devices_")
    for cpv in sorted(vardb.cpv_all()):
        cp = portage.cpv_getkey(cpv); all_cps.add(cp); cp_ver[cp] = cpv
        iuse, active = vardb.aux_get(cpv, ["IUSE", "USE"]); act_set = set(active.split())
        for f in {x.lstrip("+-") for x in iuse.split() if not x.lstrip("+-").startswith(skip)}:
            inst_map.setdefault(cp, {})[f] = inst_map.get(cp, {}).get(f, False) or (f in act_set)
    packages = []
    for cp in sorted(all_cps):
        cat, name = cp.split("/", 1); su = saved_use.get(cp, {})
        flags = [{"flag": f, "installed": iv, "effective": su.get(f, iv), "sym": f"U_{sanitize_symbol(cp)}__{sanitize_symbol(f)}"} for f, iv in sorted(inst_map.get(cp, {}).items())]
        kws, penvs = saved_kw.get(cp, set()), saved_penv.get(cp, set()); em = saved_mask.get(cp, "")
        mm = "NONE" if not em else ("FWD" if em.startswith((">=", ">")) else ("EQ" if em.startswith(("=", "~")) else "ALL"))
        sb = sanitize_symbol(cp)
        packages.append({"cp": cp, "cpv": cp_ver[cp], "cat": cat, "name": name, "flags": flags, "use_mod": any(x["effective"] != x["installed"] for x in flags), "kw_t": ("~amd64" in kws or "~*" in kws), "kw_l": ("**" in kws), "sym_kt": f"KT_{sb}", "sym_kl": f"KL_{sb}", "mask_atom": em, "mask_mode": mm, "sym_mn": f"MN_{sb}", "sym_ma": f"MA_{sb}", "sym_me": f"ME_{sb}", "sym_mf": f"MF_{sb}", "envs": [{"name": e, "initial": e in penvs, "sym": f"PE_{sb}__{sanitize_symbol(e)}"} for e in all_envs], "has_env": bool(penvs)})
    env_items = [{"fname": fn, "body": b, "desc": d, "initial": fn in env_profiles, "sym": f"EF_{sanitize_symbol(fn)}"} for fn, (b, d) in sorted(presets.items())]
    ed_envs = [{"fname": fn, "vars": [{"key": k, "initial": parse_env_vars(c).get(k, ""), "sym": f"EV_{sanitize_symbol(fn)}__{sanitize_symbol(k)}"} for k in (STD_ENV_VARS + [k for k in parse_env_vars(c) if k not in STD_ENV_VARS])], "sym_del": f"ED_{sanitize_symbol(fn)}"} for fn, c in sorted(env_profiles.items())]
    return {"packages": packages, "env_items": env_items, "ed_envs": ed_envs, "mc_file": mc_file, "mc_text": mc_text, "exp_use": exp_use, "exp_feat": exp_feat, "g_use": g_use, "g_feat": g_feat}

