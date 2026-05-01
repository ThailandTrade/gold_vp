"""
config_helpers.py - Helpers pour acceder aux configs multi-TF.

Schema multi-TF:
    ALL_INSTRUMENTS = {
        'AUS200': {
            '15m': {'risk_pct': 0.005, 'portfolio': [...]},
            '1h':  {'risk_pct': 0.005, 'portfolio': [...]},
        },
        ...
    }
    LIVE_TIMEFRAMES = ['15m', '1h']  # TFs actifs pour live/BT

Compatibilite legacy: si une entree est {'risk_pct':..., 'portfolio':...} (pas de TF imbrique),
on la traite comme TF par defaut '15m'.
"""

DEFAULT_TF = '15m'


def _is_legacy(icfg):
    """Detecte si la config instrument est en format legacy (sans TF imbrique)."""
    return isinstance(icfg, dict) and 'portfolio' in icfg


def get_inst_config(cfg, sym, tf=None):
    """Retourne le dict {risk_pct, portfolio} pour (sym, tf). None si absent."""
    all_inst = getattr(cfg, 'ALL_INSTRUMENTS', None) or getattr(cfg, 'INSTRUMENTS', None)
    if not all_inst or sym not in all_inst:
        return None
    icfg = all_inst[sym]
    if _is_legacy(icfg):
        if tf is None or tf == DEFAULT_TF:
            return icfg
        return None
    if tf is None:
        tf = DEFAULT_TF
    return icfg.get(tf)


def list_instruments(cfg, only_live=True):
    """Retourne la liste des symboles. Si only_live, filtre par LIVE_INSTRUMENTS."""
    all_inst = getattr(cfg, 'ALL_INSTRUMENTS', None) or getattr(cfg, 'INSTRUMENTS', {})
    syms = list(all_inst.keys())
    if only_live:
        live = getattr(cfg, 'LIVE_INSTRUMENTS', None)
        if live is not None:
            syms = [s for s in syms if s in live]
    return syms


def list_timeframes(cfg, sym=None):
    """Retourne les TFs configures.

    Si sym fourni: TFs disponibles pour ce sym.
    Sinon: LIVE_TIMEFRAMES (ou [DEFAULT_TF] si absent).
    """
    all_inst = getattr(cfg, 'ALL_INSTRUMENTS', None) or getattr(cfg, 'INSTRUMENTS', {})
    if sym is not None:
        icfg = all_inst.get(sym)
        if icfg is None:
            return []
        if _is_legacy(icfg):
            return [DEFAULT_TF]
        return list(icfg.keys())
    return list(getattr(cfg, 'LIVE_TIMEFRAMES', [DEFAULT_TF]))


def iter_sym_tf(cfg, only_live=True):
    """Itere sur (sym, tf, icfg) ou icfg = {risk_pct, portfolio}.

    Filtre par LIVE_INSTRUMENTS et LIVE_TIMEFRAMES si only_live.
    """
    all_inst = getattr(cfg, 'ALL_INSTRUMENTS', None) or getattr(cfg, 'INSTRUMENTS', {})
    live_inst = getattr(cfg, 'LIVE_INSTRUMENTS', None) if only_live else None
    live_tfs = list_timeframes(cfg) if only_live else None

    for sym, icfg in all_inst.items():
        if live_inst is not None and sym not in live_inst:
            continue
        if _is_legacy(icfg):
            tf = DEFAULT_TF
            if live_tfs is None or tf in live_tfs:
                if icfg.get('portfolio'):
                    yield sym, tf, icfg
        else:
            for tf, sub in icfg.items():
                if live_tfs is not None and tf not in live_tfs:
                    continue
                if sub.get('portfolio'):
                    yield sym, tf, sub


def all_sym_tf_pairs(cfg, only_live=True):
    """Liste de (sym, tf) configures."""
    return [(s, tf) for s, tf, _ in iter_sym_tf(cfg, only_live=only_live)]
