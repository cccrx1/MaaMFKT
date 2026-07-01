from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR

from common import safe_json_loads


SHOP_LIST_ROI = (60, 250, 600, 820)
SHOP_SLOTS = [
    {
        "name": "top_left",
        "name_roi": (75, 545, 165, 90),
        "sold_out_roi": (70, 430, 180, 115),
        "click_box": (75, 305, 170, 330),
    },
    {
        "name": "top_middle",
        "name_roi": (265, 545, 170, 90),
        "sold_out_roi": (260, 430, 180, 115),
        "click_box": (265, 305, 170, 330),
    },
    {
        "name": "top_right",
        "name_roi": (450, 545, 190, 90),
        "sold_out_roi": (440, 430, 190, 115),
        "click_box": (450, 305, 180, 330),
    },
    {
        "name": "bottom_left",
        "name_roi": (75, 910, 170, 90),
        "sold_out_roi": (70, 800, 180, 115),
        "click_box": (75, 675, 170, 330),
    },
    {
        "name": "bottom_middle",
        "name_roi": (265, 910, 170, 90),
        "sold_out_roi": (260, 800, 180, 115),
        "click_box": (265, 675, 170, 330),
    },
    {
        "name": "bottom_right",
        "name_roi": (450, 910, 190, 90),
        "sold_out_roi": (440, 800, 190, 115),
        "click_box": (450, 675, 180, 330),
    },
]

_LAST_TARGET_SIGNATURE = None
_PURCHASED_TARGETS = set()


def _is_word_char(ch):
    return ch.isalnum() or "\u4e00" <= ch <= "\u9fff"


def _normalize_text(text):
    return "".join(ch for ch in str(text or "") if _is_word_char(ch)).lower()


def _split_targets(raw_targets):
    if isinstance(raw_targets, list):
        return raw_targets
    if not isinstance(raw_targets, str):
        return []

    targets = []
    current = []
    for ch in raw_targets:
        if _is_word_char(ch):
            current.append(ch)
        elif current:
            targets.append("".join(current))
            current = []
    if current:
        targets.append("".join(current))
    return targets


def _parse_targets(raw_targets):
    targets = []
    seen = set()
    for candidate in _split_targets(raw_targets):
        normalized = _normalize_text(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            targets.append({"raw": str(candidate), "normalized": normalized})
    return targets


def _reset_session(targets):
    global _LAST_TARGET_SIGNATURE, _PURCHASED_TARGETS

    signature = tuple(target["normalized"] for target in targets)
    if signature != _LAST_TARGET_SIGNATURE:
        _LAST_TARGET_SIGNATURE = signature
        _PURCHASED_TARGETS = set()


def _ocr_results(context, image, roi, expected=None, threshold=0.3):
    detail = context.run_recognition_direct(
        "OCR",
        JOCR(expected=expected or [], roi=tuple(roi), threshold=threshold, only_rec=True),
        image,
    )
    return list(getattr(detail, "all_results", []) or [])


def _text_results(results):
    texts = []
    for result in results:
        text = getattr(result, "text", "")
        if text:
            texts.append(text)
    return texts


def _white_pixel_count(image, roi):
    x, y, w, h = [int(v) for v in roi]
    height, width = image.shape[:2]
    x1 = max(0, min(width, x))
    y1 = max(0, min(height, y))
    x2 = max(x1, min(width, x + w))
    y2 = max(y1, min(height, y + h))
    if x1 == x2 or y1 == y2:
        return 0

    region = image[y1:y2, x1:x2]
    # argv.image is BGR. The sold-out banner has large high-contrast white
    # letters; normal item cards only have small white quantity text here.
    bright = (region[:, :, 0] > 210) & (region[:, :, 1] > 210) & (region[:, :, 2] > 210)
    balanced = (region.max(axis=2) - region.min(axis=2)) < 45
    return int((bright & balanced).sum())


def _magenta_pixel_count(image, roi):
    x, y, w, h = [int(v) for v in roi]
    height, width = image.shape[:2]
    x1 = max(0, min(width, x))
    y1 = max(0, min(height, y))
    x2 = max(x1, min(width, x + w))
    y2 = max(y1, min(height, y + h))
    if x1 == x2 or y1 == y2:
        return 0

    region = image[y1:y2, x1:x2]
    blue = region[:, :, 0]
    green = region[:, :, 1]
    red = region[:, :, 2]
    magenta = (red > 90) & (blue > 70) & (green < 115) & (red > green + 25) & (blue > green + 5)
    return int(magenta.sum())


def _slot_texts(context, image, slot, expected):
    results = _ocr_results(context, image, slot["name_roi"], expected, threshold=0.2)
    if not results:
        results = _ocr_results(context, image, slot["name_roi"], threshold=0.2)
    return _text_results(results)


def _slot_sold_out(context, image, slot):
    texts = _text_results(
        _ocr_results(
            context,
            image,
            slot["sold_out_roi"],
            expected=["SOLD OUT", "SOLDOUT"],
            threshold=0.2,
        )
    )
    normalized = _normalize_text("".join(texts))
    white_count = _white_pixel_count(image, slot["sold_out_roi"])
    magenta_count = _magenta_pixel_count(image, slot["sold_out_roi"])
    return "soldout" in normalized or (white_count >= 900 and magenta_count >= 500), texts, white_count, magenta_count


def _read_visible_items(context, image, targets):
    expected = [target["raw"] for target in targets]
    visible = []
    for slot in SHOP_SLOTS:
        texts = _slot_texts(context, image, slot, expected)
        normalized = _normalize_text("".join(texts))
        sold_out, sold_out_texts, sold_out_white, sold_out_magenta = _slot_sold_out(context, image, slot)
        if not normalized and not sold_out_texts:
            continue
        visible.append(
            {
                "slot": slot["name"],
                "texts": texts,
                "text": "".join(texts),
                "normalized": normalized,
                "sold_out": sold_out,
                "sold_out_texts": sold_out_texts,
                "sold_out_white": sold_out_white,
                "sold_out_magenta": sold_out_magenta,
                "box": slot["click_box"],
            }
        )
    return visible


@AgentServer.custom_action("DailyShopResetExchangeSession")
class DailyShopResetExchangeSession(CustomAction):
    def run(self, context, argv, box, reco_detail):
        global _LAST_TARGET_SIGNATURE, _PURCHASED_TARGETS
        _LAST_TARGET_SIGNATURE = None
        _PURCHASED_TARGETS = set()
        return True


@AgentServer.custom_recognition("DailyShopExchangeTargetItem")
class DailyShopExchangeTargetItem(CustomRecognition):
    def analyze(self, context, argv):
        raw_param = argv.custom_recognition_param
        param = raw_param if isinstance(raw_param, dict) else safe_json_loads(raw_param, {})
        targets = _parse_targets(param.get("target_names", param.get("targets", "")))
        _reset_session(targets)

        raw_targets = [target["raw"] for target in targets]
        visible = _read_visible_items(context, argv.image, targets)
        skipped = []

        for target in targets:
            normalized_target = target["normalized"]
            if normalized_target in _PURCHASED_TARGETS:
                continue
            for item in visible:
                text = item["normalized"]
                if not text:
                    continue
                if normalized_target in text or text in normalized_target:
                    if item["sold_out"]:
                        skipped.append(
                            {
                                "target": target["raw"],
                                "slot": item["slot"],
                                "reason": "sold_out",
                                "texts": item["texts"],
                                "sold_out_texts": item["sold_out_texts"],
                                "sold_out_white": item["sold_out_white"],
                                "sold_out_magenta": item["sold_out_magenta"],
                            }
                        )
                        continue
                    _PURCHASED_TARGETS.add(normalized_target)
                    return CustomRecognition.AnalyzeResult(
                        box=item["box"],
                        detail={
                            "target": target["raw"],
                            "slot": item["slot"],
                            "visible": [entry["text"] for entry in visible],
                            "items": [
                                {
                                    "slot": entry["slot"],
                                    "text": entry["text"],
                                    "sold_out": entry["sold_out"],
                                    "sold_out_white": entry["sold_out_white"],
                                    "sold_out_magenta": entry["sold_out_magenta"],
                                }
                                for entry in visible
                            ],
                            "targets": raw_targets,
                            "skipped": skipped,
                        },
                    )

        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={
                "reason": "no_target_visible",
                "visible": [entry["text"] for entry in visible],
                "items": [
                    {
                        "slot": entry["slot"],
                        "text": entry["text"],
                        "sold_out": entry["sold_out"],
                        "sold_out_white": entry["sold_out_white"],
                        "sold_out_magenta": entry["sold_out_magenta"],
                    }
                    for entry in visible
                ],
                "targets": raw_targets,
                "skipped": skipped,
            },
        )
