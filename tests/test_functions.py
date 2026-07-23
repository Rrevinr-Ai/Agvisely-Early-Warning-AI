"""Function tests for Agvisely interview / advisory services."""

from datetime import date

import pytest

from app.services.demo_forecast_service import (
    default_stage_for_location,
    lookup_demo_forecast,
)
from app.services.dialog_service import (
    detect_intent,
    empty_dialog_state,
    extract_constraints,
    load_dialog_state,
    update_dialog_state_from_turn,
    upsert_dialog_state_message,
)
from app.services.disease_service import get_wheat_disease_advisory
from app.services.excel_advisory_service import (
    detect_crop_from_text,
    detect_stage_from_text,
    excel_advisory_service,
)
from app.services.location_service import (
    extract_location_from_message,
    merge_location_context,
)


@pytest.fixture(scope="module")
def excel():
    excel_advisory_service.reload()
    return excel_advisory_service


def test_extract_babuganj_en():
    loc = extract_location_from_message("I am a rice farmer from Babuganj.")
    assert loc.get("upazila") == "Babuganj"
    assert loc.get("district") == "Barishal"


def test_extract_babuganj_bn():
    loc = extract_location_from_message("আমি বাবুগঞ্জ থেকে বলছি")
    assert loc.get("upazila") == "Babuganj"


def test_extract_rangpur_sadar():
    loc = extract_location_from_message("আমি রংপুর সদরের ধান চাষি")
    assert loc.get("district") == "Rangpur"


def test_merge_location_overrides():
    base = {"district": "Dhaka", "upazila": None}
    spoken = {"upazila": "Babuganj", "district": "Barishal", "source": "message"}
    merged = merge_location_context(base, spoken)
    assert merged["district"] == "Barishal"
    assert merged["upazila"] == "Babuganj"


def test_demo_babuganj_numbers():
    f = lookup_demo_forecast(upazila="Babuganj", district="Barishal")
    assert f is not None
    assert f["rainfall_mm"] == 44.0
    assert f["temperature_c"] == 36.0
    assert default_stage_for_location(upazila="Babuganj") == "Booting Stage"


def test_demo_rangpur_numbers():
    f = lookup_demo_forecast(district="Rangpur", upazila="Rangpur Sadar")
    assert f is not None
    assert f["rainfall_mm"] == 10.0
    assert "Tillering" in (default_stage_for_location(district="Rangpur") or "")


def test_demo_unknown_location_none():
    assert lookup_demo_forecast(district="Nowhere", upazila="XYZ") is None


def test_detect_crop_aman_bn():
    assert detect_crop_from_text("আমার আমন ধান আছে") == "aman rice"


def test_detect_crop_rice_farmer_en():
    assert detect_crop_from_text("I am a rice farmer from Babuganj") == "aman rice"


def test_detect_crop_wheat():
    assert detect_crop_from_text("cultivate wheat") == "wheat"


def test_detect_stage_kushi_variants():
    assert detect_stage_from_text("কুশি পর্যায়ে আছে") == "Maximum Tillering Stage"
    assert detect_stage_from_text("কষি পর্যায়ে") == "Maximum Tillering Stage"


def test_detect_stage_booting():
    assert detect_stage_from_text("থোড় পর্যায়") == "Booting Stage"


def test_intent_weather_bn():
    assert detect_intent("আগামী পাঁচ দিনের আবহাওয়া পরামর্শ আছে কি?") in {
        "weather",
        "weather_crop",
    }


def test_intent_weather_crop_en():
    assert (
        detect_intent(
            "I am a rice farmer from Babuganj. Is there any weather advisory?"
        )
        == "weather_crop"
    )


def test_intent_more_advice():
    assert detect_intent("আর কোনো তথ্য বা পরামর্শ দিতে পারেন?") == "more_advice"
    assert detect_intent("Is there any other information that you can provide?") == "more_advice"


def test_intent_constraint_soil_money():
    assert detect_intent("মাটি পরীক্ষায় টাকা নেই, তাহলে কী করব?") == "constraint"


def test_extract_constraints_soil():
    c = extract_constraints("মাটি পরীক্ষা করতে অনেক টাকা লাগে, আমার টাকা নেই")
    assert "no_money_for_soil_test" in c


def test_dialog_state_roundtrip():
    messages = []
    state = empty_dialog_state()
    state = update_dialog_state_from_turn(
        state,
        "আমি রংপুর থেকে আমন ধান কুশি পর্যায়ে",
        {"district": None},
        "general_crop",
    )
    upsert_dialog_state_message(messages, state)
    loaded = load_dialog_state(messages)
    assert loaded.get("crop") == "aman rice"
    assert loaded.get("stage") == "Maximum Tillering Stage"
    assert loaded.get("district") == "Rangpur"


def test_excel_babuganj_heat_and_heavy_rain(excel):
    weather = {"source": "demo_forecast", "temperature_c": 36.0, "rainfall_mm": 44.0}
    hit = excel.lookup(
        "aman rice",
        weather=weather,
        stage="Booting Stage",
        today=date(2026, 10, 1),
    )
    assert hit and hit["source"] == "excel"
    assert "Temperature" in hit["weather_triggers"]
    assert "Rainfall" in hit["weather_triggers"]


def test_excel_rangpur_light_rain(excel):
    weather = {"source": "demo_forecast", "temperature_c": 32.0, "rainfall_mm": 10.0}
    hit = excel.lookup(
        "aman rice",
        weather=weather,
        stage="Maximum Tillering Stage",
        today=date(2026, 9, 20),
    )
    assert hit and hit["source"] == "excel"
    assert "Rainfall" in hit["weather_triggers"]


def test_weather_intent_prefers_excel_temperature_rainfall(excel):
    weather = {"source": "demo_forecast", "temperature_c": 36.0, "rainfall_mm": 44.0}
    hit = excel.lookup("aman rice", weather=weather, stage="Booting Stage")
    picked = excel.select_bullets_for_dialog(
        hit, intent="weather_crop", said_bullet_ids=[], max_bullets=6
    )
    joined = " ".join(b["text"] for b in picked)
    assert "৩৫" in joined or "তাপমাত্রা" in joined
    assert "৪৪" in joined or "বৃষ্টি" in joined


def test_excel_constraint_filters_soil_test(excel):
    weather = {"source": "demo_forecast", "temperature_c": 32.0, "rainfall_mm": 10.0}
    hit = excel.lookup(
        "aman rice",
        weather=weather,
        stage="Maximum Tillering Stage",
        today=date(2026, 9, 20),
    )
    picked = excel.select_bullets_for_dialog(
        hit,
        intent="constraint",
        constraints=["no_money_for_soil_test"],
        said_bullet_ids=[],
        max_bullets=6,
    )
    texts = " ".join(b["text"] for b in picked)
    assert "মাটি পরীক্ষা" not in texts or "এলসিসি" in texts or "গুটি" in texts


def test_excel_more_advice_skips_said(excel):
    weather = {"source": "demo_forecast", "temperature_c": 32.0, "rainfall_mm": 10.0}
    hit = excel.lookup(
        "aman rice",
        weather=weather,
        stage="Maximum Tillering Stage",
        today=date(2026, 9, 20),
    )
    all_b = excel.list_gap_bullets(hit)
    first_ids = [all_b[0]["id"], all_b[1]["id"]]
    picked = excel.select_bullets_for_dialog(
        hit,
        intent="more_advice",
        said_bullet_ids=first_ids,
        max_bullets=4,
    )
    assert picked


def test_compose_spoken_returns_ids(excel):
    weather = {"source": "demo_forecast", "temperature_c": 36.0, "rainfall_mm": 44.0}
    hit = excel.lookup("aman rice", weather=weather, stage="Booting Stage")
    speech, ids = excel.compose_spoken_advisory(
        hit, intent="weather_crop", max_bullets=3
    )
    assert len(speech) > 20
    assert len(ids) >= 1


def test_wheat_disease_content():
    data = get_wheat_disease_advisory()
    names = {d["name"] for d in data["diseases"]}
    assert "Wheat Blast" in names
    assert any("Rust" in n for n in names)
    assert "BARI Gom 33" in data["general_advisory_bn"]
    assert "BWMRI Gom 3" in data["general_advisory_bn"]
