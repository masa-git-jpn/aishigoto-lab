#!/usr/bin/env python3
"""7つの「危険検出方法」の定義。

各メソッドは (equality_fn, validity_fn) の組。
- equality_fn(a, b) -> True なら「a と b は同じ名前として衝突する」と判定
- validity_fn(name) -> True なら「name は単体として問題ない」、False なら「危険」

pair系カテゴリの判定には equality_fn を、single系カテゴリの判定には
validity_fn を使う。
"""
import unicodedata

try:
    from pathvalidate import is_valid_filename as _pv_is_valid
except ImportError:  # pragma: no cover
    _pv_is_valid = None


def _always_valid(name):
    return True


def _never_equal(a, b):
    return False


def eq_naive(a, b):
    return a == b


def eq_lower(a, b):
    return a.lower() == b.lower()


def eq_nfc(a, b):
    return unicodedata.normalize("NFC", a) == unicodedata.normalize("NFC", b)


def eq_lower_nfc(a, b):
    return unicodedata.normalize("NFC", a).lower() == unicodedata.normalize("NFC", b).lower()


def eq_nfkc_casefold(a, b):
    return unicodedata.normalize("NFKC", a).casefold() == unicodedata.normalize("NFKC", b).casefold()


def valid_pathvalidate(name):
    if _pv_is_valid is None:
        raise RuntimeError("pathvalidate not installed")
    return _pv_is_valid(name, platform="Windows")


METHODS = {
    "M1_naive_str": {
        "label": "素朴な重複チェック(文字列そのまま)",
        "eq": eq_naive,
        "valid": _always_valid,
    },
    "M2_lower": {
        "label": "lower()してから重複チェック",
        "eq": eq_lower,
        "valid": _always_valid,
    },
    "M3_nfc": {
        "label": "Unicode正規化(NFC)してから重複チェック",
        "eq": eq_nfc,
        "valid": _always_valid,
    },
    "M4_lower_nfc": {
        "label": "lower + NFC 両方してから重複チェック",
        "eq": eq_lower_nfc,
        "valid": _always_valid,
    },
    "M5_nfkc_casefold": {
        "label": "NFKC正規化 + casefold してから重複チェック",
        "eq": eq_nfkc_casefold,
        "valid": _always_valid,
    },
    "M6_pathvalidate": {
        "label": "pathvalidate(単体の妥当性チェックのみ、重複は見ない)",
        "eq": _never_equal,
        "valid": valid_pathvalidate,
    },
    "M7_full": {
        "label": "フル装備(自作): NFKC+casefoldの重複判定 + pathvalidateの単体チェック",
        "eq": eq_nfkc_casefold,
        "valid": valid_pathvalidate,
    },
}
