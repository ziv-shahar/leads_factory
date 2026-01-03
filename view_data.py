#!/usr/bin/env python3
"""Quick script to view all data in the database."""
from src.db.session import get_db
from src.db.models import Entity, Event, RawEvent, LeadCurrent, LeadStateHistory
import json


def view_all_data():
    """Display all data from the database."""
    with get_db() as db:
        print("\n" + "=" * 80)
        print("RAW EVENTS (Files Ingested)")
        print("=" * 80)
        raw_events = db.query(RawEvent).all()
        for raw in raw_events:
            print(f"\nID: {raw.id}")
            print(f"  File: {raw.file_path}")
            print(f"  Source: {raw.source}")
            print(f"  Hash: {raw.content_hash[:16]}...")
            print(f"  Ingested: {raw.ingested_at}")
            print(f"  Status: {raw.status}")

        print("\n" + "=" * 80)
        print("ENTITIES (Companies)")
        print("=" * 80)
        entities = db.query(Entity).all()
        for entity in entities:
            print(f"\nID: {entity.id}")
            print(f"  Canonical Name: {entity.canonical_name}")
            print(f"  Normalized: {entity.normalized_name}")
            print(f"  Domain: {entity.domain}")
            print(f"  Website: {entity.website_url}")
            print(f"  LinkedIn: {entity.linkedin_url}")
            if entity.hq_city or entity.hq_state:
                hq = f"{entity.hq_city or 'Unknown'}, {entity.hq_state or 'Unknown'}"
                print(f"  HQ: {hq}")
            else:
                print(f"  HQ: None")

        print("\n" + "=" * 80)
        print("EVENTS (Extracted Events)")
        print("=" * 80)
        events = db.query(Event).order_by(Event.event_time.desc()).all()
        for event in events:
            print(f"\nID: {event.id}")
            print(f"  Entity: {event.entity.canonical_name if event.entity else 'Unknown'}")
            print(f"  Type: {event.event_type}")
            print(f"  Summary: {event.strict.get('summary', 'N/A')}")
            print(f"  Confidence: {event.extraction_confidence}")
            print(f"  Date: {event.event_time or event.ingest_time}")
            print(f"  Source: {event.source}")

            # Show key facts
            key_facts = event.strict.get('key_facts', {})
            if key_facts:
                print(f"  Key Facts:")
                if key_facts.get('amount'):
                    print(f"    Amount: {key_facts['amount']}")
                # Handle both old (location) and new (city/state) formats
                if key_facts.get('city') or key_facts.get('state'):
                    city = key_facts.get('city', 'Unknown')
                    state = key_facts.get('state', 'Unknown')
                    print(f"    Location: {city}, {state} (NEW FORMAT)")
                elif key_facts.get('location'):
                    print(f"    Location: {key_facts['location']} (OLD FORMAT)")
                if key_facts.get('people'):
                    print(f"    People: {', '.join(key_facts['people'])}")
                if key_facts.get('dates'):
                    print(f"    Dates: {', '.join(key_facts['dates'])}")
                if key_facts.get('companies'):
                    print(f"    Companies: {', '.join(key_facts['companies'])}")
                if key_facts.get('products'):
                    print(f"    Products: {', '.join(key_facts['products'])}")

            # Show source URL if available
            source_url = event.strict.get('source_url')
            if source_url:
                print(f"  Source URL: {source_url}")

            # Show dynamic signals details
            if event.dynamic_signals:
                print(f"  Dynamic Signals ({len(event.dynamic_signals)}):")
                for signal in event.dynamic_signals:
                    signal_type = signal.get('signal_type', 'unknown')
                    description = signal.get('description', 'N/A')
                    print(f"    • [{signal_type}] {description}")
                    evidence = signal.get('evidence_quote')
                    if evidence:
                        print(f"      Evidence: \"{evidence[:100]}...\"" if len(evidence) > 100 else f"      Evidence: \"{evidence}\"")


        print("\n" + "=" * 80)
        print("LEADS (Current State)")
        print("=" * 80)
        leads = db.query(LeadCurrent).order_by(LeadCurrent.score.desc()).all()
        for lead in leads:
            print(f"\nEntity: {lead.entity.canonical_name if lead.entity else 'Unknown'}")
            print(f"  Score: {lead.score}")
            print(f"  Confidence: {lead.confidence_score:.2f}")
            print(f"  Status: {lead.status}")
            print(f"  Last Updated: {lead.last_updated_at}")
            if lead.reasons:
                print(f"  Event Count: {lead.reasons.get('event_count', 0)}")
                print(f"  Unique Sources: {lead.reasons.get('unique_sources', 0)}")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Raw Events: {len(raw_events)}")
        print(f"Total Entities: {len(entities)}")
        print(f"Total Events: {len(events)}")
        print(f"Total Leads: {len(leads)}")
        print("=" * 80 + "\n")


def view_lead_details(entity_id=None):
    """View detailed breakdown for a specific lead."""
    with get_db() as db:
        if entity_id:
            lead = db.query(LeadCurrent).filter(LeadCurrent.entity_id == entity_id).first()
            leads = [lead] if lead else []
        else:
            leads = db.query(LeadCurrent).order_by(LeadCurrent.score.desc()).all()

        for lead in leads:
            print("\n" + "=" * 80)
            print(f"LEAD DETAILS: {lead.entity.canonical_name if lead.entity else 'Unknown'}")
            print("=" * 80)
            print(f"Score: {lead.score}")
            print(f"Confidence: {lead.confidence_score:.2f}")
            print(f"Status: {lead.status}")

            if lead.reasons:
                print(f"\nScore Breakdown:")
                print(f"  Total Score: {lead.reasons.get('total_score', 0)}")
                print(f"  Confidence: {lead.reasons.get('confidence', 0):.2f}")
                print(f"  Event Count: {lead.reasons.get('event_count', 0)}")
                print(f"  Unique Sources: {lead.reasons.get('unique_sources', 0)}")

                breakdown = lead.reasons.get('breakdown', [])
                if breakdown:
                    print(f"\n  Top Contributing Factors:")
                    for i, item in enumerate(breakdown[:10], 1):
                        score = item.get('score_contribution', 0)
                        item_type = item.get('type', item.get('event_type', 'unknown'))
                        desc = item.get('description', item.get('summary', 'N/A'))
                        print(f"    {i}. [{item_type}] +{score} pts: {desc[:60]}...")

            # Show all events for this entity
            events = db.query(Event).filter(Event.entity_id == lead.entity_id).all()
            print(f"\n  All Events ({len(events)}):")
            for event in events:
                print(f"    • {event.event_type}: {event.strict.get('summary', 'N/A')[:70]}")
                print(f"      Confidence: {event.extraction_confidence:.2f}, Signals: {len(event.dynamic_signals)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "details":
            entity_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
            view_lead_details(entity_id)
        else:
            print("Usage: python view_data.py [details] [entity_id]")
    else:
        view_all_data()
