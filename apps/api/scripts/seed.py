from __future__ import annotations

import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select 

from app.core.aliases import user_alias_for_lot 
from app.core.ids import iso_utc, new_public_id, utcnow
from app.core.security import hash_password 
from app.db.session import SessionLocal  
from app.models import Bid, Lot, User  
from app.services import wallet as wallet_service  
from app.services.lot_state import next_minimum_bid_cents  
from app.services.settlement import close_and_settle_lot  

DEV_PASSWORD = "artbid-demo-2026"
SEED_MARKER = "seed@artbid.local"

ARTWORKS = {
    "hero": {
        "externalId": "aic_25784",
        "title": "Retrato em azul",
        "artist": "Escola Europeia",
        "date": "c. 1880",
        "imageUrl": "/images/art-hero.jpg",
        "imageAlt": "Retrato clássico em moldura",
        "description": "Retrato de escola europeia, óleo sobre tela. Snapshot local para demonstração.",
    },
    "salon": {
        "externalId": "aic_09571",
        "title": "O salão dourado",
        "artist": "Mestre anónimo",
        "date": "Século XIX",
        "imageUrl": "/images/art-salon.jpg",
        "imageAlt": "Salão clássico com luz dourada",
        "description": "Interior de salão oitocentista. Snapshot local para demonstração.",
    },
    "vangogh": {
        "externalId": "aic_14620",
        "title": "Autorretrato",
        "artist": "Vincent van Gogh",
        "date": "1887",
        "imageUrl": "/images/art-vangogh.jpg",
        "imageAlt": "Pintura demonstrativa de autorretrato",
        "description": "Autorretrato de 1887. Snapshot local para demonstração.",
    },
    "scarf": {
        "externalId": "aic_18402",
        "title": "Jovem com touca branca",
        "artist": "Escola holandesa",
        "date": "c. 1720",
        "imageUrl": "/images/art-scarf.jpg",
        "imageAlt": "Retrato demonstrativo de jovem",
        "description": "Retrato de escola holandesa. Snapshot local para demonstração.",
    },
    "blue": {
        "externalId": "aic_20684",
        "title": "Dama em azul",
        "artist": "Escola Europeia",
        "date": "c. 1890",
        "imageUrl": "/images/art-blue.jpg",
        "imageAlt": "Retrato feminino em tons azuis",
        "description": "Retrato feminino em tons azuis. Snapshot local para demonstração.",
    },
}


def _get_or_create_user(session, *, email: str, display_name: str, role: str) -> User:
    user = session.scalar(select(User).where(User.email_normalized == email))
    if user:
        return user
    user = User(
        public_id=new_public_id("usr"),
        display_name=display_name,
        email_normalized=email,
        email_display=email,
        password_hash=hash_password(DEV_PASSWORD),
        role=role,
    )
    session.add(user)
    session.flush()
    if role == "bidder":
        wallet_service.get_or_create_wallet(session, user)
    return user


def _deposit(session, user: User, amount: int) -> None:
    wallet = wallet_service.lock_wallet(session, user.id)
    if wallet.total_cents >= amount:
        return
    delta = amount - wallet.total_cents
    wallet_service.apply_movement(
        session,
        wallet,
        type="deposit",
        amount_cents=delta,
        total_delta_cents=delta,
        description="Depósito simulado de créditos",
        user_id=user.id,
    )


def _ensure_lot(session, *, auctioneer: User, artwork: dict, number_hint: str | None, **kwargs) -> Lot:
    existing = session.scalar(select(Lot).where(Lot.external_artwork_id == artwork["externalId"], Lot.auctioneer_id == auctioneer.id))
    if existing:
        return existing
    from app.services.lots import allocate_lot_number

    lot = Lot(
        public_id=new_public_id("lot"),
        number=number_hint or allocate_lot_number(session),
        auctioneer_id=auctioneer.id,
        title=kwargs.get("title") or artwork["title"],
        artist=artwork["artist"],
        artwork_date=artwork["date"],
        description=artwork["description"],
        image_url=artwork["imageUrl"],
        image_alt=artwork["imageAlt"],
        external_artwork_id=artwork["externalId"],
        artwork_source="Art Institute of Chicago",
        artwork_snapshot=artwork,
        status=kwargs.get("status", "scheduled"),
        starting_bid_cents=kwargs["starting_bid_cents"],
        minimum_increment_cents=kwargs["minimum_increment_cents"],
        starts_at=kwargs["starts_at"],
        ends_at=kwargs["ends_at"],
    )
    session.add(lot)
    session.flush()
    from app.audit.service import record_business_event

    record_business_event(
        session,
        lot=lot,
        type="lot.created",
        actor_ref=auctioneer.public_id,
        data={
            "number": lot.number,
            "startingBidCents": lot.starting_bid_cents,
            "minimumIncrementCents": lot.minimum_increment_cents,
            "startsAt": iso_utc(lot.starts_at),
            "endsAt": iso_utc(lot.ends_at),
            "externalArtworkId": artwork["externalId"],
        },
        sse_type="lot.state.changed",
        sse_payload={
            "status": lot.status,
            "currentBidCents": 0,
            "nextMinimumBidCents": lot.starting_bid_cents,
            "endsAt": iso_utc(lot.ends_at),
            "bidCount": 0,
        },
    )
    return lot


def seed() -> dict:
    now = utcnow()
    session = SessionLocal()
    try:
        auctioneer = _get_or_create_user(
            session, email="leiloeiro@demo.artbid", display_name="Leiloeiro Demo", role="auctioneer"
        )
        bidder_a = _get_or_create_user(
            session, email="licitante@demo.artbid", display_name="Licitante Demo", role="bidder"
        )
        bidder_b = _get_or_create_user(
            session, email="coleccionador@demo.artbid", display_name="Coleccionador Demo", role="bidder"
        )
        session.flush()

        _deposit(session, bidder_a, 12_000_000)
        _deposit(session, bidder_b, 9_000_000)
        session.flush()

        live_lot = _ensure_lot(
            session,
            auctioneer=auctioneer,
            artwork=ARTWORKS["hero"],
            number_hint="0148",
            status="live",
            starting_bid_cents=800_000,
            minimum_increment_cents=50_000,
            starts_at=now - timedelta(hours=3),
            ends_at=now + timedelta(minutes=42),
        )
        if live_lot.bid_count == 0:
            history = [(bidder_a, 800_000), (bidder_b, 850_000), (bidder_a, 900_000),
                       (bidder_b, 950_000), (bidder_a, 1_000_000), (bidder_b, 1_100_000),
                       (bidder_a, 1_250_000), (bidder_b, 1_400_000), (bidder_a, 1_550_000),
                       (bidder_b, 1_700_000), (bidder_a, 1_790_000), (bidder_b, 1_840_000)]
            previous_bid: Bid | None = None
            for index, (bidder, amount) in enumerate(history):
                if previous_bid is not None:
                    previous_bid.status = "outbid"
                    session.flush()
                bid = Bid(
                    public_id=new_public_id("bid"),
                    lot_id=live_lot.id,
                    bidder_id=bidder.id,
                    amount_cents=amount,
                    status="leading",
                    sequence_in_lot=live_lot.bid_count + 1,
                    created_at=now - timedelta(minutes=50 - index),
                )
                session.add(bid)
                session.flush()
                live_lot.bid_count += 1
                live_lot.current_bid_cents = amount
                live_lot.leading_bid_id = bid.id
                session.flush()
                previous_bid = bid
            assert previous_bid is not None
            wallet_b = wallet_service.lock_wallet(session, bidder_b.id)
            wallet_service.reservation_for_bid(
                session,
                wallet_b,
                bid_id=previous_bid.id,
                lot_id=live_lot.id,
                amount_cents=previous_bid.amount_cents,
                description="Saldo reservado · Retrato em azul",
            )
            from app.audit.service import record_business_event

            for bid in session.scalars(select(Bid).where(Bid.lot_id == live_lot.id).order_by(Bid.id)).all():
                owner = session.get(User, bid.bidder_id)
                assert owner is not None
                record_business_event(
                    session,
                    lot=live_lot,
                    type="bid.accepted",
                    actor_alias=user_alias_for_lot(live_lot.public_id, owner.public_id),
                    actor_ref=owner.public_id,
                    amount_cents=bid.amount_cents,
                    occurred_at=bid.created_at,
                    data={"bidId": bid.public_id, "bidCount": bid.sequence_in_lot},
                    sse_type="bid.accepted",
                    sse_payload={
                        "bid": {
                            "id": bid.public_id,
                            "bidderAlias": user_alias_for_lot(live_lot.public_id, owner.public_id),
                            "amountCents": bid.amount_cents,
                            "createdAt": iso_utc(bid.created_at),
                        },
                        "currentBidCents": bid.amount_cents,
                        "nextMinimumBidCents": bid.amount_cents + live_lot.minimum_increment_cents,
                        "bidCount": bid.sequence_in_lot,
                    },
                )
            session.flush()

        scheduled_lot = _ensure_lot(
            session,
            auctioneer=auctioneer,
            artwork=ARTWORKS["salon"],
            number_hint="0149",
            status="scheduled",
            starting_bid_cents=1_200_000,
            minimum_increment_cents=100_000,
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=3),
        )

        live_lot_two = _ensure_lot(
            session,
            auctioneer=auctioneer,
            artwork=ARTWORKS["vangogh"],
            number_hint="0150",
            status="live",
            starting_bid_cents=3_000_000,
            minimum_increment_cents=50_000,
            starts_at=now - timedelta(hours=6),
            ends_at=now + timedelta(hours=4),
        )
        if live_lot_two.bid_count == 0:
            bid = Bid(
                public_id=new_public_id("bid"),
                lot_id=live_lot_two.id,
                bidder_id=bidder_a.id,
                amount_cents=3_250_000,
                status="leading",
                sequence_in_lot=1,
                created_at=now - timedelta(minutes=30),
            )
            session.add(bid)
            session.flush()
            live_lot_two.bid_count = 1
            live_lot_two.current_bid_cents = 3_250_000
            live_lot_two.leading_bid_id = bid.id
            session.flush()
            wallet_a = wallet_service.lock_wallet(session, bidder_a.id)
            wallet_service.reservation_for_bid(
                session,
                wallet_a,
                bid_id=bid.id,
                lot_id=live_lot_two.id,
                amount_cents=3_250_000,
                description="Saldo reservado · Autorretrato",
            )
            from app.audit.service import record_business_event

            record_business_event(
                session,
                lot=live_lot_two,
                type="bid.accepted",
                actor_alias=user_alias_for_lot(live_lot_two.public_id, bidder_a.public_id),
                actor_ref=bidder_a.public_id,
                amount_cents=bid.amount_cents,
                occurred_at=bid.created_at,
                data={"bidId": bid.public_id, "bidCount": 1},
                sse_type="bid.accepted",
                sse_payload={
                    "bid": {
                        "id": bid.public_id,
                        "bidderAlias": user_alias_for_lot(live_lot_two.public_id, bidder_a.public_id),
                        "amountCents": bid.amount_cents,
                        "createdAt": iso_utc(bid.created_at),
                    },
                    "currentBidCents": bid.amount_cents,
                    "nextMinimumBidCents": next_minimum_bid_cents(live_lot_two),
                    "bidCount": 1,
                },
            )
            session.flush()

        ended_lot = _ensure_lot(
            session,
            auctioneer=auctioneer,
            artwork=ARTWORKS["blue"],
            number_hint="0092",
            status="live",
            starting_bid_cents=2_000_000,
            minimum_increment_cents=100_000,
            starts_at=now - timedelta(days=10),
            ends_at=now - timedelta(days=9),
        )
        if ended_lot.settled_at is None and ended_lot.bid_count == 0:
            winning = Bid(
                public_id=new_public_id("bid"),
                lot_id=ended_lot.id,
                bidder_id=bidder_a.id,
                amount_cents=2_780_000,
                status="leading",
                sequence_in_lot=1,
                created_at=now - timedelta(days=9, hours=1),
            )
            session.add(winning)
            session.flush()
            ended_lot.bid_count = 1
            ended_lot.current_bid_cents = 2_780_000
            ended_lot.leading_bid_id = winning.id
            session.flush()
            wallet_winner = wallet_service.lock_wallet(session, bidder_a.id)
            wallet_service.reservation_for_bid(
                session,
                wallet_winner,
                bid_id=winning.id,
                lot_id=ended_lot.id,
                amount_cents=2_780_000,
                description="Saldo reservado · Dama em azul",
            )
            from app.audit.service import record_business_event

            record_business_event(
                session,
                lot=ended_lot,
                type="bid.accepted",
                actor_alias=user_alias_for_lot(ended_lot.public_id, bidder_a.public_id),
                actor_ref=bidder_a.public_id,
                amount_cents=winning.amount_cents,
                occurred_at=winning.created_at,
                data={"bidId": winning.public_id, "bidCount": 1},
                sse_type="bid.accepted",
                sse_payload={"bid": {"id": winning.public_id,
                                     "bidderAlias": user_alias_for_lot(ended_lot.public_id, bidder_a.public_id),
                                     "amountCents": winning.amount_cents,
                                     "createdAt": iso_utc(winning.created_at)},
                             "currentBidCents": winning.amount_cents,
                             "nextMinimumBidCents": ended_lot.current_bid_cents + ended_lot.minimum_increment_cents,
                             "bidCount": 1},
            )
            session.flush()
            close_and_settle_lot(session, ended_lot.id, now=now)

        session.commit()
        from app.realtime.publisher import dispatch_pending_sync

        dispatch_pending_sync(session, limit=200)

        return {
            "users": {
                "auctioneer": "leiloeiro@demo.artbid",
                "bidders": ["licitante@demo.artbid", "coleccionador@demo.artbid"],
                "password": DEV_PASSWORD,
            },
            "lots": {
                "live": live_lot.public_id,
                "scheduled": scheduled_lot.public_id,
                "live2": live_lot_two.public_id,
                "ended": ended_lot.public_id,
            },
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import json

    print(json.dumps(seed(), indent=2, ensure_ascii=False))
