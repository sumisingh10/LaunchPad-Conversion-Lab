"""Utility module for seed demo.
Provides utility routines used by setup and support workflows.
"""
from sqlalchemy import select, text

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Campaign, User, Variant, VariantVersion
from app.models.enums import CampaignObjective, CampaignStatus, CreatedBySystem, VariantSource


def run_seed() -> None:
    """Seed demo user, campaign, and baseline variant data."""
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "demo@launchpad.ai"))
        if not user:
            user = User(email="demo@launchpad.ai", hashed_password=hash_password("demo1234"), name="Demo User")
            db.add(user)
            db.flush()

        if settings.demo_reset_on_start:
            if db.bind and db.bind.dialect.name == "postgresql":
                db.execute(
                    text(
                        "TRUNCATE TABLE campaigns RESTART IDENTITY CASCADE"
                    )
                )
            else:
                campaigns_to_reset = db.scalars(select(Campaign).where(Campaign.user_id == user.id)).all()
                for existing in campaigns_to_reset:
                    db.delete(existing)
            db.flush()

        demo_campaigns = [
            {
                "name": "Spring Accessories Push",
                "product_title": "AeroLite Travel Backpack",
                "product_category": "Bags",
                "product_description": "Lightweight urban backpack for commuters and weekend travel.",
                "objective": CampaignObjective.CTR,
                "audience_segment": "Mobile-first deal seekers",
                "constraints_json": {"required_trust_phrase": "warranty", "max_headline_chars": 80},
                "primary_kpi": "CTR",
                "status": CampaignStatus.RUNNING,
                "assets": {
                    "hero": {
                        "headline": "Meet the AeroLite Backpack for Everyday Travel",
                        "subheadline": "Smart storage, low weight, and built-in weather protection.",
                        "cta_text": "Shop Now",
                        "trust_callout": "1-year warranty and free returns",
                    },
                    "bullets": [
                        "Ultra-light design for daily commutes",
                        "Padded laptop sleeve with quick access",
                        "Water-resistant exterior for all-weather use",
                    ],
                    "banner": {"text": "Launch week: save 15%", "badge": "New"},
                    "meta": {"strategy_tag": "baseline", "rationale": "Seed variant for live demos"},
                },
            },
            {
                "name": "Weekend Fitness Drop",
                "product_title": "FlexGrip Training Duffel",
                "product_category": "Fitness",
                "product_description": "Compact duffel optimized for gym-to-office commuters.",
                "objective": CampaignObjective.ATC,
                "audience_segment": "Returning loyalty members",
                "constraints_json": {"required_trust_phrase": "free returns", "max_headline_chars": 82},
                "primary_kpi": "ATC",
                "status": CampaignStatus.RUNNING,
                "assets": {
                    "hero": {
                        "headline": "Pack Faster With The FlexGrip Training Duffel",
                        "subheadline": "Gym-ready compartments and day-long comfort in one carry.",
                        "cta_text": "Claim Launch Offer",
                        "trust_callout": "Free returns and secure checkout",
                    },
                    "bullets": [
                        "Dedicated shoe compartment keeps essentials clean",
                        "Reinforced straps built for daily use",
                        "Slim profile fits locker and overhead bins",
                    ],
                    "banner": {"text": "Member bonus: 10% off this week", "badge": "Member"},
                    "meta": {"strategy_tag": "baseline", "rationale": "Secondary seeded campaign for demos"},
                },
            },
            {
                "name": "New Arrivals Launch",
                "product_title": "CloudZip Everyday Sling",
                "product_category": "Accessories",
                "product_description": "Modern crossbody sling for on-the-go essentials.",
                "objective": CampaignObjective.CONVERSION,
                "audience_segment": "First-time mobile shoppers",
                "constraints_json": {"required_trust_phrase": "warranty", "max_headline_chars": 84},
                "primary_kpi": "CONVERSION",
                "status": CampaignStatus.RUNNING,
                "assets": {
                    "hero": {
                        "headline": "Go Hands-Free With The CloudZip Everyday Sling",
                        "subheadline": "Minimal look, maximum utility, and fast daily access.",
                        "cta_text": "Shop New Arrival",
                        "trust_callout": "1-year warranty and easy returns",
                    },
                    "bullets": [
                        "Quick-access front pocket for daily essentials",
                        "Adjustable strap for crossbody or shoulder fit",
                        "Weather-ready shell for city commutes",
                    ],
                    "banner": {"text": "New arrival price drop for a limited time", "badge": "New"},
                    "meta": {"strategy_tag": "baseline", "rationale": "Conversion-focused seeded campaign"},
                },
            },
            {
                "name": "Urban Accessories Sprint",
                "product_title": "CityStride Organizer Tote",
                "product_category": "Accessories",
                "product_description": "Multi-pocket tote for workday carry and weekend errands.",
                "objective": CampaignObjective.CTR,
                "audience_segment": "Style-conscious commuters",
                "constraints_json": {"required_trust_phrase": "free returns", "max_headline_chars": 86},
                "primary_kpi": "CTR",
                "status": CampaignStatus.RUNNING,
                "assets": {
                    "hero": {
                        "headline": "Upgrade Daily Carry With The CityStride Organizer Tote",
                        "subheadline": "Designed for polished looks, quick access, and all-day comfort.",
                        "cta_text": "Explore The Collection",
                        "trust_callout": "Free returns and secure checkout",
                    },
                    "bullets": [
                        "Structured compartments keep tech and essentials organized",
                        "Durable fabric built for city commutes and errands",
                        "Minimal profile with premium hardware accents",
                    ],
                    "banner": {"text": "Limited launch pricing on top accessories", "badge": "Limited"},
                    "meta": {"strategy_tag": "baseline", "rationale": "City-style baseline campaign"},
                },
            },
        ]

        for demo in demo_campaigns:
            campaign = db.scalar(select(Campaign).where(Campaign.user_id == user.id, Campaign.name == demo["name"]))
            if not campaign:
                campaign = Campaign(
                    user_id=user.id,
                    name=demo["name"],
                    product_title=demo["product_title"],
                    product_category=demo["product_category"],
                    product_description=demo["product_description"],
                    objective=demo["objective"],
                    audience_segment=demo["audience_segment"],
                    constraints_json=demo["constraints_json"],
                    primary_kpi=demo["primary_kpi"],
                    status=demo["status"],
                )
                db.add(campaign)
                db.flush()

            variant = db.scalar(select(Variant).where(Variant.campaign_id == campaign.id, Variant.name == "Baseline"))
            if variant:
                continue

            assets = demo["assets"]
            variant = Variant(
                campaign_id=campaign.id,
                name="Baseline",
                strategy_tag="baseline",
                assets_json=assets,
                source=VariantSource.HUMAN,
            )
            db.add(variant)
            db.flush()

            version = VariantVersion(
                variant_id=variant.id,
                version_number=1,
                assets_json=assets,
                parent_version_id=None,
                created_by_user_id=user.id,
                created_by_system=CreatedBySystem.SYSTEM,
                change_summary="Initial seeded baseline variant",
            )
            db.add(version)

        db.commit()


if __name__ == "__main__":
    run_seed()
    print("Seed complete: demo user is ready (credentials documented in README).")
