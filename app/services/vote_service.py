import re
import uuid

from app.database.vote_repository import (
    create_vote,
    get_vote,
    record_choice,
    get_voter_choice,
)
from app.database.product_repository import get_products_by_slugs


VOTER_TOKEN_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{8,128}$")

# Ticimax sayfasındaki productId/urunKartiId, tabrano-ai'daki product_card_id
# ile birebir eşleşmiyor (bu DB kendi sıra numarasını kullanıyor). Bu yüzden
# oylamalarda ürünler URL slug'ı (ör. "rex-orta-sehpa") ile tanımlanır.
SLUG_PATTERN = re.compile(r"^[a-z0-9-]{1,200}$")




def normalize_slug(value):

    value = str(value or "").strip()
    value = re.sub(r"^https?://[^/]+/?", "", value)
    value = value.strip("/").lower()

    return value




def _light_product(row):

    return {
        "id": row[0],
        "name": row[2],
        "price": float(row[8]) if row[8] is not None else None,
        "url": row[9],
        "image": row[10],
    }




def _format_vote_state(vote_row, voter_choice):

    vote_id, product_a_slug, product_b_slug, created_at, votes_a, votes_b = vote_row

    votes_a = votes_a or 0
    votes_b = votes_b or 0
    total = votes_a + votes_b

    percent_a = round((votes_a / total) * 100) if total else 0
    percent_b = 100 - percent_a if total else 0

    rows = get_products_by_slugs([product_a_slug, product_b_slug])
    by_slug = {normalize_slug(row[9]): _light_product(row) for row in rows}

    return {
        "vote_id": str(vote_id),
        "product_a": by_slug.get(product_a_slug),
        "product_b": by_slug.get(product_b_slug),
        "votes_a": votes_a,
        "votes_b": votes_b,
        "total_votes": total,
        "percent_a": percent_a,
        "percent_b": percent_b,
        "voter_choice": voter_choice,
        "created_at": created_at.isoformat() if created_at else None,
    }




def create_vote_session(product_a_id, product_b_id):

    product_a_slug = normalize_slug(product_a_id)
    product_b_slug = normalize_slug(product_b_id)

    if not product_a_slug or not product_b_slug:
        raise ValueError("product_a_id ve product_b_id zorunludur.")

    if not SLUG_PATTERN.match(product_a_slug) or not SLUG_PATTERN.match(product_b_slug):
        raise ValueError("Geçersiz ürün tanımlayıcısı.")

    if product_a_slug == product_b_slug:
        raise ValueError("Karşılaştırma için iki farklı ürün seçilmelidir.")

    rows = get_products_by_slugs([product_a_slug, product_b_slug])
    found_slugs = {normalize_slug(row[9]) for row in rows}

    if product_a_slug not in found_slugs or product_b_slug not in found_slugs:
        raise ValueError("Ürünlerden biri bulunamadı.")

    vote_id = uuid.uuid4()

    create_vote(vote_id, product_a_slug, product_b_slug)

    return _format_vote_state(get_vote(vote_id), voter_choice=None)




def submit_vote(vote_id, choice, voter_token):

    if choice not in ("A", "B"):
        raise ValueError("choice 'A' ya da 'B' olmalıdır.")

    if not voter_token or not VOTER_TOKEN_PATTERN.match(voter_token):
        raise ValueError("Geçersiz voter_token.")

    vote_row = get_vote(vote_id)

    if not vote_row:
        raise LookupError("Oylama bulunamadı.")

    record_choice(vote_id, choice, voter_token)

    voter_choice = get_voter_choice(vote_id, voter_token)

    return _format_vote_state(get_vote(vote_id), voter_choice)




def get_vote_state(vote_id, voter_token=None):

    vote_row = get_vote(vote_id)

    if not vote_row:
        raise LookupError("Oylama bulunamadı.")

    if voter_token and not VOTER_TOKEN_PATTERN.match(voter_token):
        voter_token = None

    voter_choice = get_voter_choice(vote_id, voter_token) if voter_token else None

    return _format_vote_state(vote_row, voter_choice)
