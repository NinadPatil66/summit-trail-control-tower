"""Free text with known answers: supplier emails, carrier notes, return comments.

Every message comes from a template whose blanks we fill, so we know the true
answer for each one. Those answers go to label files, which later score Cortex AI.
"""
from datetime import timedelta

import pandas as pd

from .config import make_rng
from .master import read_master
from .writers import write_csv, write_ndjson

# ---------- supplier delay emails (English) ----------
REASONS = [("PRODUCTION", "a production backlog at our plant"), ("MATERIALS", "a shortage of raw materials"),
           ("SHIPPING", "port congestion"), ("QUALITY", "a failed quality inspection"),
           ("WEATHER", "severe weather at our facility")]
EMAIL_TEMPLATES = [
    ("Delay on {po}", "Hi team,\n\nOur shipment for {po} will be late due to {reason}. The new ship date is {new_date}.\n\nRegards,\n{contact}, {supplier}"),
    ("{po} - revised date", "Hello,\n\nUnfortunately {po} is delayed because of {reason}. We now expect to ship on {new_date}. Sorry for the trouble.\n\n{contact}"),
    ("Update: purchase order {po}", "Good morning,\n\nQuick update on PO {po}: {reason} pushed our schedule. Revised promise date: {new_date}.\n\nThanks,\n{supplier}"),
    ("Shipping change for {po}", "Team,\n\nPlease note {po} will not ship as planned. Cause: {reason}. Updated ETA {new_date}.\n\nBest,\n{contact}"),
    ("RE: {po}", "Hi,\n\nFollowing up on {po}. Due to {reason} we have moved the ship date to {new_date}. Let us know if this works.\n\n{contact}\n{supplier}"),
    ("Heads up on {po}", "Hello Summit Trail team,\n\n{reason_cap} is affecting order {po}. Expect delivery around {new_date}.\n\nKind regards,\n{contact}"),
]
DATE_FORMATS = ["%Y-%m-%d", "%B %d, %Y", "%m/%d/%Y", "%d %b %Y"]

# ---------- carrier exception notes (English, Spanish, French) ----------
NOTE_TEMPLATES = {
    "weather": {
        "en": ["Delayed by severe weather near {city}. New ETA in {days} days.", "Storm closed roads around {city}; shipment held at terminal."],
        "es": ["Retraso por condiciones climáticas en {city}. Nueva entrega en {days} días.", "Tormenta cerró carreteras cerca de {city}; envío retenido en terminal."],
        "fr": ["Retard dû aux intempéries près de {city}. Nouvelle livraison dans {days} jours.", "Tempête : routes fermées autour de {city}, colis retenu au terminal."]},
    "address": {
        "en": ["Consignee address incomplete, driver could not deliver. Need suite number.", "Wrong ZIP on label; package rerouted via {city}."],
        "es": ["Dirección del destinatario incompleta; el conductor no pudo entregar.", "Código postal incorrecto en la etiqueta; paquete desviado por {city}."],
        "fr": ["Adresse du destinataire incomplète, le chauffeur n'a pas pu livrer.", "Code postal erroné sur l'étiquette ; colis réacheminé via {city}."]},
    "damage": {
        "en": ["Pallet arrived damaged at {city} hub, {days} cartons crushed.", "Visible water damage on outer cartons. Photos taken."],
        "es": ["Tarima llegó dañada al centro de {city}, {days} cajas aplastadas.", "Daños por agua visibles en las cajas exteriores."],
        "fr": ["Palette endommagée au hub de {city}, {days} cartons écrasés.", "Dégâts des eaux visibles sur les cartons extérieurs."]},
    "capacity": {
        "en": ["No trailer capacity out of {city} today, rolled to next departure.", "Linehaul at capacity; shipment delayed {days} days."],
        "es": ["Sin capacidad de remolque desde {city} hoy; pasa a la siguiente salida.", "Ruta troncal saturada; envío retrasado {days} días."],
        "fr": ["Pas de capacité de remorque au départ de {city} aujourd'hui, reporté au prochain départ.", "Ligne saturée ; envoi retardé de {days} jours."]},
    "customs": {
        "en": ["Held at customs pending commercial invoice.", "Customs inspection at {city}, release expected in {days} days."],
        "es": ["Retenido en aduana en espera de la factura comercial.", "Inspección aduanera en {city}; liberación prevista en {days} días."],
        "fr": ["Bloqué en douane en attente de la facture commerciale.", "Contrôle douanier à {city}, mainlevée prévue sous {days} jours."]},
    "other": {
        "en": ["Customer requested delivery appointment for next week.", "Driver reported dock closed at arrival time."],
        "es": ["El cliente pidió cita de entrega para la próxima semana.", "El conductor reportó el muelle cerrado a la llegada."],
        "fr": ["Le client a demandé un rendez-vous de livraison la semaine prochaine.", "Le chauffeur a trouvé le quai fermé à l'arrivée."]},
}
CATEGORY_WEIGHTS = {"weather": 0.25, "address": 0.15, "damage": 0.15, "capacity": 0.2, "customs": 0.05, "other": 0.2}
HUB_CITIES = ["Memphis", "Atlanta", "Dallas", "Louisville", "Columbus", "Reno", "Ontario", "Allentown"]

# ---------- return comments (English) ----------
RETURN_TEMPLATES = {
    "positive": ["Great quality, exactly as described. Returning only because I ordered two.",
                 "Arrived fast and works well, just not the color I wanted.", "Love it, but a gift duplicate. Would buy again."],
    "neutral": ["Returning because the size was not what I needed.", "Item is fine but I changed my mind.",
                "Ordered the wrong model by mistake."],
    "negative": ["Broke after two uses. Very disappointed.", "Package arrived damaged and parts were missing.",
                 "Much smaller than the photos suggest. Poor value."],
}
OPENERS = ["", "Hi, ", "Honestly, ", "FYI: ", "Note: "]


def random_day(cfg, rng):
    start, end = cfg["history"]["start"], cfg["history"]["end"]
    return start + timedelta(days=int(rng.integers(0, (end - start).days + 1)))


def weighted_choice(options, rng):
    keys = list(options)
    weights = [options[k] for k in keys]
    total = sum(weights)
    return keys[int(rng.choice(len(keys), p=[w / total for w in weights]))]


def fake_keys(cfg, rng, suppliers, carriers):
    """Stand-in keys until real POs and shipments exist in Snowflake (Module 2)."""
    n_po, n_shp = 5000, 20000
    pos = pd.DataFrame({"po_number": [f"PO-{i:07d}" for i in range(1, n_po + 1)],
                        "supplier_code": rng.choice(suppliers["supplier_code"].to_numpy(), n_po),
                        "po_date": [random_day(cfg, rng) for _ in range(n_po)]})
    shipments = pd.DataFrame({"shipment_id": [f"SHP-{i:07d}" for i in range(1, n_shp + 1)],
                              "carrier_code": rng.choice(carriers["carrier_code"].to_numpy(), n_shp)})
    return pos, shipments


def build_emails(pos, suppliers, cfg, rng):
    names = dict(zip(suppliers["supplier_code"], suppliers["name"]))
    messages, labels = [], []
    for i in range(cfg["text"]["supplier_emails"]):
        po = pos.iloc[int(rng.integers(len(pos)))]
        reason_code, reason = REASONS[int(rng.integers(len(REASONS)))]
        new_date = po["po_date"] + timedelta(days=int(rng.integers(20, 75)))
        subject, body = EMAIL_TEMPLATES[int(rng.integers(len(EMAIL_TEMPLATES)))]
        fill = {"po": po["po_number"], "reason": reason, "reason_cap": reason[0].upper() + reason[1:],
                "new_date": new_date.strftime(DATE_FORMATS[int(rng.integers(len(DATE_FORMATS)))]),
                "supplier": names[po["supplier_code"]], "contact": "Order Desk"}
        email_id = f"EM-{i + 1:06d}"
        messages.append({"email_id": email_id, "supplier_code": po["supplier_code"],
                         "sent_at": po["po_date"] + timedelta(days=int(rng.integers(3, 15))),
                         "subject": subject.format(**fill), "body": body.format(**fill)})
        labels.append({"email_id": email_id, "po_number": po["po_number"],
                       "new_promised_date": new_date, "reason": reason_code})
    return messages, pd.DataFrame(labels)


def build_notes(shipments, cfg, rng):
    langs = cfg["traps"]["note_languages"]
    planted = cfg["planted"]["carrier_storm_delays"]["carrier"]
    messages, labels = [], []
    for i in range(cfg["text"]["carrier_notes"]):
        shp = shipments.iloc[int(rng.integers(len(shipments)))]
        weights = dict(CATEGORY_WEIGHTS)
        if shp["carrier_code"] == planted:
            weights["weather"] *= 2            # the planted carrier reports more weather trouble
        category = weighted_choice(weights, rng)
        lang = weighted_choice(langs, rng)
        options = NOTE_TEMPLATES[category][lang]
        text = options[int(rng.integers(len(options)))].format(
            city=HUB_CITIES[int(rng.integers(len(HUB_CITIES)))], days=int(rng.integers(1, 6)))
        note_id = f"CN-{i + 1:06d}"
        messages.append({"note_id": note_id, "shipment_id": shp["shipment_id"], "carrier_code": shp["carrier_code"],
                         "created_at": random_day(cfg, rng), "note": text})
        labels.append({"note_id": note_id, "category": category, "language": lang})
    return messages, pd.DataFrame(labels)


def build_returns(products, cfg, rng):
    skus = products["sku_code"].to_numpy()
    messages, labels = [], []
    for i in range(cfg["text"]["return_comments"]):
        sentiment = weighted_choice({"positive": 0.2, "neutral": 0.35, "negative": 0.45}, rng)
        options = RETURN_TEMPLATES[sentiment]
        comment = OPENERS[int(rng.integers(len(OPENERS)))] + options[int(rng.integers(len(options)))]
        return_id = f"RT-{i + 1:06d}"
        messages.append({"return_id": return_id, "sku_code": str(skus[int(rng.integers(len(skus)))]),
                         "created_at": random_day(cfg, rng), "comment": comment})
        labels.append({"return_id": return_id, "sentiment": sentiment})
    return messages, pd.DataFrame(labels)


def generate_text(cfg):
    rng = make_rng(cfg, "text")
    out = cfg["paths"]["out_dir"]
    suppliers, carriers = read_master(cfg, "supplier"), read_master(cfg, "carrier")
    products = read_master(cfg, "product")
    pos, shipments = fake_keys(cfg, rng, suppliers, carriers)

    emails, email_labels = build_emails(pos, suppliers, cfg, rng)
    notes, note_labels = build_notes(shipments, cfg, rng)
    returns, return_labels = build_returns(products, cfg, rng)
    return [
        write_ndjson(emails, out, "docs/text/supplier_emails.ndjson"),
        write_ndjson(notes, out, "docs/text/carrier_notes.ndjson"),
        write_ndjson(returns, out, "docs/text/return_comments.ndjson"),
        write_csv(email_labels, out, "labels/supplier_email_labels.csv"),
        write_csv(note_labels, out, "labels/carrier_note_labels.csv"),
        write_csv(return_labels, out, "labels/return_comment_labels.csv"),
    ]