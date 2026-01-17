"""
Supabase client wrapper that mimics SQLAlchemy interface.

This wrapper provides a SQLAlchemy-like interface for Supabase REST API,
allowing minimal code changes when switching from PostgreSQL to Supabase client.
"""
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import uuid
from supabase import create_client, Client

from src.config import SUPABASE_URL, SUPABASE_KEY
from src.db.models import Base, Entity, Event, RawEvent, LeadCurrent, LeadStateHistory


# Table name mapping
TABLE_MAP = {
    'Entity': 'entities',
    'Event': 'events',
    'RawEvent': 'raw_events',
    'LeadCurrent': 'leads_current',
    'LeadStateHistory': 'lead_state_history'
}


class SupabaseQuery:
    """Mimics SQLAlchemy Query interface for Supabase."""

    def __init__(self, model_class: Type[Base], supabase: Client):
        self.model_class = model_class
        self.supabase = supabase
        self.table_name = TABLE_MAP[model_class.__name__]
        self._filters = []
        self._limit_value = None

    def filter(self, *conditions):
        """Add filter conditions."""
        for condition in conditions:
            self._filters.append(condition)
        return self

    def first(self) -> Optional[Any]:
        """Get first matching record."""
        query = self.supabase.table(self.table_name).select("*")

        # Apply filters
        for filter_expr in self._filters:
            query = self._apply_filter(query, filter_expr)

        # Limit to 1
        query = query.limit(1)

        result = query.execute()

        if result.data and len(result.data) > 0:
            return self._dict_to_model(result.data[0])
        return None

    def all(self) -> List[Any]:
        """Get all matching records."""
        query = self.supabase.table(self.table_name).select("*")

        # Apply filters
        for filter_expr in self._filters:
            query = self._apply_filter(query, filter_expr)

        if self._limit_value:
            query = query.limit(self._limit_value)

        result = query.execute()

        return [self._dict_to_model(row) for row in result.data]

    def count(self) -> int:
        """Count matching records."""
        query = self.supabase.table(self.table_name).select("id", count="exact")

        # Apply filters
        for filter_expr in self._filters:
            query = self._apply_filter(query, filter_expr)

        result = query.execute()
        return result.count if result.count is not None else 0

    def limit(self, value: int):
        """Limit results."""
        self._limit_value = value
        return self

    def _apply_filter(self, query, filter_expr):
        """Apply a filter expression to the query."""
        # Parse SQLAlchemy-style filter expression
        # e.g., Entity.domain == "example.com"
        # This is simplified - handles basic equality comparisons

        if hasattr(filter_expr, 'left') and hasattr(filter_expr, 'right'):
            # Binary expression (==, !=, etc.)
            column_name = str(filter_expr.left.key)
            operator = filter_expr.operator.__name__
            value = filter_expr.right.value

            if operator == 'eq':
                query = query.eq(column_name, value)
            elif operator == 'ne':
                query = query.neq(column_name, value)
            elif operator == 'gt':
                query = query.gt(column_name, value)
            elif operator == 'lt':
                query = query.lt(column_name, value)
            elif operator == 'like_op':
                # Convert SQL LIKE to Supabase pattern
                query = query.like(column_name, value)

        return query

    def _dict_to_model(self, data: Dict) -> Any:
        """Convert dictionary to model instance."""
        # Create instance without calling __init__
        instance = object.__new__(self.model_class)

        # Set attributes
        for key, value in data.items():
            # Convert ISO datetime strings to datetime objects
            if isinstance(value, str) and ('_at' in key or '_time' in key):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass
            setattr(instance, key, value)

        return instance


class SupabaseSession:
    """Mimics SQLAlchemy Session interface for Supabase."""

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._pending_adds = []
        self._committed = False

    def query(self, model_class: Type[Base]) -> SupabaseQuery:
        """Create a query for the given model."""
        return SupabaseQuery(model_class, self.supabase)

    def add(self, instance: Any):
        """Add an instance to be inserted."""
        self._pending_adds.append(instance)

    def flush(self):
        """Flush pending adds to database and update IDs."""
        for instance in self._pending_adds:
            self._insert_instance(instance)
        self._pending_adds.clear()

    def commit(self):
        """Commit transaction (flush any pending adds)."""
        self.flush()
        self._committed = True

    def rollback(self):
        """Rollback transaction."""
        self._pending_adds.clear()
        self._committed = False

    def close(self):
        """Close session."""
        if not self._committed and self._pending_adds:
            # Auto-commit if there are pending adds
            self.commit()

    def _insert_instance(self, instance: Any):
        """Insert a single instance into Supabase."""
        table_name = TABLE_MAP[instance.__class__.__name__]
        data = self._model_to_dict(instance)

        # Insert and get the result
        result = self.supabase.table(table_name).insert(data).execute()

        if result.data and len(result.data) > 0:
            # Update instance with returned ID
            returned_row = result.data[0]
            if 'id' in returned_row:
                instance.id = returned_row['id']

            # Update any other auto-generated fields
            for key, value in returned_row.items():
                if not hasattr(instance, key) or getattr(instance, key) is None:
                    setattr(instance, key, value)

    def _model_to_dict(self, instance: Any) -> Dict:
        """Convert model instance to dictionary for Supabase."""
        data = {}

        # Get all column attributes
        for key in dir(instance):
            if key.startswith('_') or key in ['metadata', 'registry']:
                continue

            value = getattr(instance, key, None)

            # Skip methods, relationships, and None values for auto-increment IDs
            if callable(value) or hasattr(value, '__relationship__'):
                continue

            # Skip auto-increment IDs if they're None
            if key == 'id' and value is None:
                # Check if this model uses auto-increment ID
                if instance.__class__.__name__ in ['Entity', 'RawEvent', 'LeadCurrent', 'LeadStateHistory']:
                    continue

            # Convert datetime to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()

            # Convert UUID to string
            if isinstance(value, uuid.UUID):
                value = str(value)

            # Only include if value is not None or if it's a required field
            if value is not None:
                data[key] = value
            elif key in ['strict', 'dynamic_signals', 'entity_metadata', 'reasons']:
                # These JSONB fields should default to dict/list
                if key in ['dynamic_signals']:
                    data[key] = []
                else:
                    data[key] = {}

        return data


def get_supabase_session() -> SupabaseSession:
    """Get a new Supabase session."""
    return SupabaseSession()
